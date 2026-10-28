"""Смоук-тест дашборда: каждый экран открывается и рисуется без ошибок.

Поднимает бэкенд на синтетических данных (backend/tests/seed_demo.py) в своей
схеме Postgres, обходит все экраны в headless Chromium и проверяет: загрузка
закончилась, нет плашки «Не удалось загрузить данные», нет ошибок в консоли и
исключений на странице, ни один ответ /api/* не 5xx. С каждого экрана --
скриншот в frontend/tests/screenshots/.

Кнопки не нажимаются: POST тратит квоту YouTube и деньги LLM. Рабочие данные не
трогаются: своя схема nf_smoke_<hex>, после прогона удаляется.

    make frontend-test
"""
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
import warnings
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
SHOTS = Path(__file__).resolve().parent / "screenshots"

# 27 ключей ROUTES из router.js (до разбивки -- из app.js) + глубокие ссылки
# на объекты из seed_demo.py.
ROUTES = [
    "overview", "find", "viral", "channels", "categories", "keywords", "tags",
    "tracker", "alerts", "ideas", "brainNext", "language", "transcripts", "clusters", "titles", "saved", "packaging", "metadata", "calendar",
    "niches", "enter", "own", "data", "help", "mcp", "plan", "admin", "profile",
    "niche/demo", "channel/UC0000000000000000000a", "channel/UC0000000000000000000f",
    "channel-compare/UC0000000000000000000a,UC0000000000000000000f", "brief/avid000",
    "brief/avid000?gap=how%20to%20start%20a%20tiny%20AI%20lab%3F",
    "compare/avid000,avid001",
]

LOCALES = ["ru", "en", "tr"]

# Кириллица, допустимая в английском интерфейсе: данные из seed_demo.py
# (название канала), а не текст интерфейса.
DATA_CYRILLIC = ["Нейросети по-русски"]

READY_JS = """() => {
  const v = document.querySelector('#view');
  return !!v && !v.querySelector('.skeleton-page') && v.textContent.trim().length > 0;
}"""


def _env(schema):
    # Пустой ключ перекрывает корневой .env (dotenv не перезаписывает заданные
    # переменные), LLM выключен: ни квоты, ни денег.
    return dict(os.environ, NICHE_DB_SCHEMA=schema, YOUTUBE_API_KEY="", LLM_PROVIDER="none")


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _drop_schema(env, schema):
    code = ("import infrastructure.postgres as db\n"
            "c = db.get_conn()\n"
            f"c.execute('DROP SCHEMA IF EXISTS \"{schema}\" CASCADE')\n"
            "c.commit()\n"
            "c.close()\n")
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env,
                             check=False, capture_output=True, text=True)
    if result.returncode != 0:
        # Не роняем иначе зелёный прогон -- но не молчим: без этого предупреждения
        # схема nf_smoke_* тихо остаётся в базе.
        warnings.warn(
            f"failed to drop schema {schema!r} (exit {result.returncode}):\n{result.stderr}",
            stacklevel=2)


def _wait_healthy(url, proc, log_path, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            pytest.fail(f"uvicorn exited early:\n{log_path.read_text()[-3000:]}")
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=5) as r:
                if r.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.5)
    pytest.fail(f"/api/health not ready in {timeout}s:\n{log_path.read_text()[-3000:]}")


@pytest.fixture(scope="session")
def base_url(tmp_path_factory):
    schema = f"nf_smoke_{uuid.uuid4().hex[:8]}"
    env = _env(schema)
    proc = None
    try:
        subprocess.run([sys.executable, "tests/seed_demo.py"], cwd=BACKEND, env=env, check=True)
        port = _free_port()
        log_path = tmp_path_factory.mktemp("uvicorn") / "server.log"
        with open(log_path, "w") as log:
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT)
        url = f"http://127.0.0.1:{port}"
        _wait_healthy(url, proc, log_path)
        yield url
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        _drop_schema(env, schema)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _new_page(browser, locale="ru"):
    """Страница с выбранным языком интерфейса: nf.locale в localStorage ставится
    до загрузки скриптов. Проверки текста ниже написаны по-русски -- по умолчанию ru.
    Закрывать через page.context.close()."""
    ctx = browser.new_context(viewport={"width": 1400, "height": 900}, locale="en-US")
    ctx.add_init_script(f"localStorage.setItem('nf.locale', '{locale}')")
    return ctx.new_page()


def _ui_cyrillic(text):
    """Куски кириллицы, которые не объясняются данными из seed_demo.py."""
    # слова одной строки: аватар «Н» и название канала под ним -- разные куски
    pieces = re.findall(r"[А-Яа-яЁё][А-Яа-яЁё\-]*(?:[ \t]+[А-Яа-яЁё][А-Яа-яЁё\-]*)*", text)
    return sorted({p for p in pieces if not any(p in d for d in DATA_CYRILLIC)})


def _is_benign_console(text):
    # Ответ 4xx/5xx браузер сам пишет в консоль как "Failed to load resource".
    # 4xx для экранов -- штатно (например, 428 без ключа YouTube), а 5xx
    # ловится отдельно по ответам.
    return text.startswith("Failed to load resource")


def _router_js_route_keys():
    """Ключи объекта ROUTES из frontend/router.js (без глубоких ссылок)."""
    text = (ROOT / "frontend" / "router.js").read_text(encoding="utf-8")
    block = re.search(r"const\s+ROUTES\s*=\s*\{(.*?)\n\};", text, re.S)
    assert block, "router.js: не нашли блок `const ROUTES = { ... };`"
    return re.findall(r"^\s*([A-Za-z_$][\w$]*)\s*:\s*\{", block.group(1), re.M)


def test_routes_list_matches_router_js():
    # Экран, добавленный в router.js, но не в ROUTES здесь, тестировался бы
    # молча никогда -- эта проверка ловит рассинхронизацию без браузера/сервера.
    expected = {r for r in ROUTES if "/" not in r}
    actual = set(_router_js_route_keys())
    assert actual == expected, (
        f"ROUTES в test_smoke.py разошёлся с router.js: "
        f"отсутствуют в тесте {sorted(actual - expected)}, "
        f"лишние в тесте {sorted(expected - actual)}"
    )


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("route", ROUTES)
def test_screen_renders_without_errors(browser, base_url, route, locale):
    page = _new_page(browser, locale)
    problems = []
    page.on("console", lambda m: m.type == "error" and not _is_benign_console(m.text)
            and problems.append(f"console.error: {m.text}"))
    page.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
    page.on("response", lambda r: "/api/" in r.url and r.status >= 500
            and problems.append(f"HTTP {r.status}: {r.url}"))
    try:
        page.goto(f"{base_url}/#/{route}")
        page.wait_for_function(READY_JS, timeout=30000)
        page.wait_for_load_state("networkidle")
        SHOTS.mkdir(exist_ok=True)
        shot = re.sub(r"[^\w.-]+", "_", route)
        page.screenshot(path=str(SHOTS / f"{shot}.{locale}.png"), full_page=True)
        text = page.inner_text("#view")
        chrome = page.inner_text(".sidebar") + "\n" + page.inner_text(".topbar")
    finally:
        page.context.close()
    assert "Не удалось загрузить данные" not in text and "Could not load the data" not in text, text[:500]
    assert not problems, "\n".join(problems)
    if locale == "en":
        # кнопка языка законно показывает «Русский» -- остальное должно быть английским
        left = _ui_cyrillic(text + "\n" + chrome.replace("Русский", ""))
        assert not left, f"#/{route} (en): русский текст в интерфейсе: {left}"



@pytest.mark.parametrize("route,expected", [
    ("overview", ["YouTube Brain", "Genel Bakış", "Nişleri keşfet"]),
    ("find", ["Niş Keşfi", "Filtreleri temizle"]),
    ("viral", ["Viral Videolar", "Küçük Kanalların Viral Videoları"]),
    ("ideas", ["Fikir Analizi", "Video Fikri Analizi"]),
    ("categories", ["Popüler Kategoriler"]),
    ("keywords", ["Yükselen Anahtar Kelimeler"]),
])
def test_youtube_brain_turkish_navigation_and_core_screens(browser, base_url, route, expected):
    """The Turkish browser preference renders translated core UI; quota buttons stay untouched."""
    page = _new_page(browser, "tr")
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    try:
        page.goto(f"{base_url}/#/{route}")
        page.wait_for_function(READY_JS, timeout=30000)
        page.wait_for_load_state("networkidle")
        assert page.title() == "YouTube Brain | YouTube Araştırma Merkezi"
        assert page.locator(".brand-name").inner_text() == "YouTube Brain"
        assert page.evaluate("document.documentElement.lang") == "tr"
        assert page.evaluate("localStorage.getItem('nf.locale')") == "tr"
        combined = page.inner_text("#view") + page.inner_text(".sidebar") + page.inner_text(".topbar")
        for phrase in expected:
            assert phrase in combined, (route, phrase, combined[:900])
        assert not errors, errors
    finally:
        page.context.close()


def test_turkish_language_can_be_selected_and_preserved(browser, base_url):
    """Keep original en->ru click behavior; add ru->tr without a full reload."""
    page = _new_page(browser, "en")
    try:
        page.goto(f"{base_url}/#/overview")
        page.wait_for_function(READY_JS, timeout=30000)
        page.evaluate("window.sameDoc = true")
        page.select_option("#langSelect", "ru")
        page.wait_for_function("document.documentElement.lang === 'ru'")
        page.select_option("#langSelect", "tr")
        page.wait_for_function("document.documentElement.lang === 'tr'")
        page.wait_for_function(
            "() => document.querySelector('#crumbSection').textContent === 'Genel Bakış'"
        )
        assert page.evaluate("window.sameDoc") is True
        assert page.evaluate("localStorage.getItem('nf.locale')") == "tr"
        assert page.inner_text(".brand-name") == "YouTube Brain"
    finally:
        page.context.close()












def test_brain_channel_compare_link_normalizes_ids_without_storage(browser, base_url):
    """Only 2-3 safe, unique channel IDs in a shareable URL; no stored basket."""
    page = _new_page(browser, "tr")
    try:
        page.goto(f"{base_url}/#/overview")
        page.wait_for_function(READY_JS)
        result = page.evaluate("""async () => {
            const { normalizeChannelIds, channelCompareHref } =
              await import('/channel-compare-utils.js');
            const a = 'UC0000000000000000000a';
            const f = 'UC0000000000000000000f';
            const b = 'UC0000000000000000000b';
            const normal = 'UC' + 'a'.repeat(22);
            return {
                demoIds: normalizeChannelIds([a, a, f, b, normal]),
                fullLength: normalizeChannelIds([normal]).length,
                malformed: normalizeChannelIds([a, '%E0%A4%A', 'UCbad', '<script>']),
                href: channelCompareHref([a, f]),
                single: channelCompareHref([a]),
                basket: localStorage.getItem('nf.channel-compare'),
            };
        }""")
        assert result["demoIds"] == [
            "UC0000000000000000000a", "UC0000000000000000000f",
            "UC0000000000000000000b"]
        assert result["fullLength"] == 1
        assert result["malformed"] == ["UC0000000000000000000a"]
        assert result["href"] == (
            "#/channel-compare/UC0000000000000000000a,UC0000000000000000000f")
        assert result["single"] is None
        assert result["basket"] is None
    finally:
        page.context.close()


def test_brain_channel_compare_table_displays_existing_data_and_missing(browser, base_url):
    """Two read-only GETs; missing 30d growth is a dash, not a fabricated zero."""
    import json

    a = "UC0000000000000000000a"
    f = "UC0000000000000000000f"
    sample = {
        "found": True,
        "profile": {"title": "Archive Alpha", "subscribers": 1800,
                    "videoCount": 100},
        "performance": {"videosAnalysed": 20, "medianViewsPerVideo": 4200,
                        "medianViewsPerSubscriber": 2.3, "viralSkew": 1.7},
        "cadence": {"uploadsInPeriod": 4, "uploadsPerWeekLifetime": 1.5,
                    "shortsSharePercent": 25.0},
        "growth": {"30d": {"subscribers": None, "views": None}},
        "snapshots": 1,
        "topOutliers": [{"outlierScore": 3.4}],
    }
    page = _new_page(browser, "tr")
    requests = []

    def respond(route):
        requests.append(route.request.url)
        channel_id = route.request.url.split("/api/channels/")[1].split("?")[0]
        if channel_id == f:
            route.fulfill(status=404, content_type="application/json",
                          body='{"detail":"channel missing locally"}')
        else:
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(sample))

    page.route("**/api/channels/*", respond)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{base_url}/#/channel-compare/{a},{f}")
        page.wait_for_selector(".channel-compare-table", timeout=30000)
        txt = page.inner_text("#view")
        assert "Rakip Kanalları Karşılaştır" in txt
        assert "Archive Alpha" in txt
        assert "Arşivde incelenen video" in txt
        assert "30 günlük ölçülebilen abone artışı / gün" in txt
        assert f in txt  # missing channel notice retains the requested ID
        assert "yerel arşivde bulunamadı" in txt
        assert page.locator(".channel-compare-table tbody tr").count() == 13
        assert len(requests) == 2 and all("/api/channels/" in url for url in requests)
        assert all("period=" in url for url in requests)
        assert not errors, errors
    finally:
        page.context.close()


def test_brain_channel_compare_selection_needs_two_channels(browser, base_url):
    """No POST or discovery: selection only changes the hash URL."""
    import json

    ids = ["UC0000000000000000000a", "UC0000000000000000000f"]
    channels = [{"channelId": cid, "channelTitle": "Sample " + str(i),
                 "subscribers": 200 + i, "multiplier": 3.5, "strength": 2,
                 "videosInWindow": 4} for i, cid in enumerate(ids)]
    page = _new_page(browser, "tr")
    page.route("**/api/outlier-channels*", lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps({
            "channels": channels, "hint": None})))
    try:
        page.goto(f"{base_url}/#/channels")
        page.wait_for_selector(".js-compare-channel", timeout=30000)
        btn = page.locator("#compareChannelsBtn")
        assert btn.is_disabled()
        picks = page.locator(".js-compare-channel")
        assert picks.count() == 2
        picks.nth(0).check()
        assert btn.is_disabled()
        picks.nth(1).check()
        assert btn.is_enabled()
        btn.click()
        page.wait_for_function("""() => location.hash.startsWith('#/channel-compare/')""")
        assert page.evaluate("location.hash") == "#/channel-compare/" + ",".join(ids)
    finally:
        page.context.close()


def test_brain_competitor_evidence_panel_is_displayed_without_extra_quota(browser, base_url):
    """Use already-loaded channel endpoints; display archive and snapshot limitations."""
    page = _new_page(browser, "tr")
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{base_url}/#/channel/UC0000000000000000000a")
        page.wait_for_selector("#channelEvidenceTitle", timeout=30000)
        assert "Rakip Kanal Veri Özeti" in page.inner_text("#view")
        assert page.locator(".channel-evidence-item").count() == 4
        text = page.locator(".channel-evidence-card").inner_text()
        assert "Toplanan / kanalda bildirilen video" in text
        assert "Kanal istatistik kayıtları" in text
        assert "24 saatlik hızı ölçülen" in text
        assert "Vektörü hesaplanan" in text
        assert "başarı olasılığı veya güven puanı değildir" in text
        assert page.locator('.channel-evidence-card a[href="#/data"]').count() == 1
        assert not errors, errors
    finally:
        page.context.close()


def test_brain_channel_evidence_calculations_are_honest_about_missing_data(browser, base_url):
    page = _new_page(browser, "tr")
    try:
        page.goto(f"{base_url}/#/overview")
        page.wait_for_function(READY_JS)
        cases = page.evaluate("""async () => {
            const { channelEvidence } = await import('/channel-evidence.js');
            return [
                channelEvidence(
                    {profile: {videoCount: 120}, performance: {videosAnalysed: 65},
                     growth: {'24h': {views: {delta: 0, per_day: 0}},
                              '7d': {views: null, subscribers: null},
                              '30d': {subscribers: {delta: 12}}}},
                    {videos: [{vph24h: null}, {vph24h: 0}, {vph24h: 12}]},
                    {count: 5}, {videosEmbedded: 40}),
                channelEvidence(
                    {profile: {videoCount: 0}, performance: {videosAnalysed: 0},
                     growth: {}},
                    {videos: []}, {count: 0}, {}),
                channelEvidence(
                    {profile: {videoCount: 3}, performance: {videosAnalysed: 9}},
                    {videos: [{vph24h: null}]}, {count: 1},
                    {videosEmbedded: -1}),
            ];
        }""")
        complete, empty, inconsistent = cases
        assert complete["archivePercent"] == 54
        assert complete["vphAvailable"] == 2 and complete["sampledCount"] == 3
        assert complete["observedGrowthWindows"] == ["24h", "30d"]
        assert complete["archiveIncomplete"] is True
        assert empty["archivePercent"] is None
        assert empty["historyInsufficient"] is True
        assert empty["embeddingMissing"] is False
        assert inconsistent["archivePercent"] is None
        assert inconsistent["velocityInsufficient"] is True
        assert inconsistent["embedded"] is None
    finally:
        page.context.close()


def test_brain_niche_evidence_table_does_not_call_coverage_confidence(browser, base_url):
    """The ranking page shows exact sample sizes and a visible unscored reason."""
    page = _new_page(browser, "tr")
    fake = {
        "niches": [
            {
                "niche": "history", "label": "History", "videos": 60, "channels": 6,
                "recentVideos": 26, "score": 61, "band": "high", "coverage": 0.8,
                "status": "stable", "confidence": "good",
                "breakdown": [
                    {"key": k, "value": 1 if i < 4 else None,
                     "points": 50 if i < 4 else None, "weight": w, "label": k}
                    for i, (k, w) in enumerate([
                        ("demand", 25), ("supply", 20), ("newcomers", 20),
                        ("rpm", 15), ("template", 10), ("policy", 10)])
                ]
            },
            {
                "niche": "thin", "label": "Thin", "videos": 3, "channels": 1,
                "recentVideos": 1, "score": None, "band": None,
                "coverage": 0.4, "reason": "insufficient-data",
                "status": "insufficient-data", "confidence": "insufficient",
                "breakdown": [
                    {"key": k, "value": 1 if k in ("demand", "rpm") else None,
                     "points": 50 if k in ("demand", "rpm") else None,
                     "weight": w, "label": k}
                    for k, w in [
                        ("demand", 25), ("supply", 20), ("newcomers", 20),
                        ("rpm", 15), ("template", 10), ("policy", 10)]
                ]
            },
        ]
    }
    import json
    page.route("**/api/niches/ranking*", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=json.dumps(fake, ensure_ascii=False)))
    problems = []
    page.on("pageerror", lambda err: problems.append(str(err)))
    try:
        page.goto(f"{base_url}/#/enter")
        page.wait_for_function(READY_JS)
        page.wait_for_selector(".niche-evidence-line")
        txt = page.inner_text("#view")
        assert "60 video · 6 kanal · son 30 günde 26 video" in txt
        assert "3 video · 1 kanal · son 30 günde 1 video" in txt
        assert "Bilinen ölçüt ağırlığı: %80" in txt
        assert "Bilinen ölçüt ağırlığı: %40" in txt
        assert "yeterli veri yok: niş eğilimi hesaplanamıyor" in txt
        assert "güven" in page.locator(".evidence-weight").first.get_attribute("data-tip")
        assert not problems, problems
    finally:
        page.context.close()


def test_brain_niche_evidence_unknown_and_zero_are_not_rounded_into_claims(browser, base_url):
    page = _new_page(browser, "tr")
    try:
        page.goto(f"{base_url}/#/overview")
        page.wait_for_function(READY_JS)
        results = page.evaluate("""async () => {
            const { evidence } = await import('/niche-evidence.js');
            return [
                evidence({videos: 0, channels: 0, recentVideos: 0, score: 0,
                    coverage: 0, breakdown: []}),
                evidence({videos: 3, channels: undefined, recentVideos: null,
                    score: null, coverage: undefined}),
                evidence({videos: 10, channels: -2, recentVideos: 900,
                    score: null, coverage: 2, reason: 'not-known'}),
            ];
        }""")
        zero, missing, invalid = results
        assert zero["hasScore"] is True and zero["knownWeightPct"] == 0
        assert zero["distinctChannels"] == 0 and zero["recentVideos"] == 0
        assert missing["distinctChannels"] is None and missing["knownWeightPct"] is None
        assert invalid["distinctChannels"] is None and invalid["knownWeightPct"] is None
        assert invalid["missingReason"] is None
    finally:
        page.context.close()


def test_brain_archive_coverage_is_global_and_visible(browser, base_url):
    """Evidence metadata is clearly scoped and does not pretend to be a niche-specific score."""
    page = _new_page(browser, "tr")
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(f"{base_url}/#/overview")
        page.wait_for_function(READY_JS)
        page.locator("#archiveCoverageTitle").wait_for()
        assert page.locator(".coverage-item").count() == 4
        text = page.locator(".coverage-card").inner_text()
        assert "Arşiv Veri Durumu" in text
        assert "seçilen nişe özel değildir" in text
        assert "güvenilirlik puanı değildir" in text
        assert "Geçmiş kaydı olan videolar" in text
        assert "Vektörü olan videolar" in text
        assert page.locator('.coverage-card a[href="#/data"]').count() == 1
        assert not errors, errors
    finally:
        page.context.close()


def test_brain_archive_coverage_derives_counts_without_guessing(browser, base_url):
    """Zero denominator, missing keys and inconsistent counters never become invented percentages."""
    page = _new_page(browser, "tr")
    try:
        page.goto(f"{base_url}/#/overview")
        page.wait_for_function(READY_JS)
        calculated = page.evaluate("""async () => {
            const { archiveCoverage } = await import('/coverage-insights.js');
            return [
                archiveCoverage({ videosTotal: 200, videosPublishedInPeriod: 4,
                  videosWithHistory: 80, videosWithCategory: 160 },
                  { videos_without_embedding: 25 }),
                archiveCoverage({ videosTotal: 0, videosPublishedInPeriod: 0,
                  videosWithHistory: 0, videosWithCategory: 0 },
                  { videos_without_embedding: 0 }),
                archiveCoverage({ videosTotal: 7, videosWithHistory: 8,
                  videosWithCategory: null }, { videos_without_embedding: 9 }),
                archiveCoverage({}, {}),
            ];
        }""")
        complete, empty, inconsistent, missing = calculated
        assert complete["period"] == 4 and complete["periodSparse"] is True
        assert complete["historyPct"] == 40
        assert complete["categoriesPct"] == 80
        assert complete["vectors"] == 175 and complete["vectorsPct"] == 88
        assert empty["historyPct"] is None and empty["vectorsPct"] is None
        assert inconsistent["historyPct"] is None and inconsistent["vectors"] is None
        assert missing["total"] is None and missing["periodPct"] is None
    finally:
        page.context.close()


def test_brain_navigation_groups_cover_all_routes_and_open_deep_links(browser, base_url):
    """Grouping is purely visual: no existing route disappears or becomes inaccessible."""
    page = _new_page(browser, "tr")
    try:
        page.goto(f"{base_url}/#/overview")
        page.wait_for_function(READY_JS)
        groups = page.locator("#nav details.nav-group")
        assert groups.count() == 4
        assert [x.strip() for x in groups.locator("summary").all_inner_texts()] == [
            "Araştırma", "Rakipler ve Kanallar", "İçerik Stüdyosu", "Sistem ve Destek"
        ]
        nav_urls = page.locator("#nav a.nav-item").evaluate_all(
            "(items) => items.map(item => item.getAttribute('href'))"
        )
        assert len(nav_urls) == len(set(nav_urls)) == 27
        assert set(nav_urls) == {f"#/{route}" for route in ROUTES if "/" not in route}
        assert page.locator('a.nav-item[href="#/overview"]').get_attribute("aria-current") == "page"
        assert not page.locator('details[data-group="system"]').evaluate("(el) => el.open")
        page.goto(f"{base_url}/#/profile")
        page.wait_for_function(READY_JS)
        assert page.locator('details[data-group="system"]').evaluate("(el) => el.open")
        assert page.locator('a.nav-item[href="#/profile"]').get_attribute("aria-current") == "page"
    finally:
        page.context.close()


def test_brain_navigation_preferences_survive_reload_and_languages(browser, base_url):
    page = _new_page(browser, "tr")
    try:
        page.goto(f"{base_url}/#/overview")
        page.wait_for_function(READY_JS)
        group = page.locator('details[data-group="research"]')
        assert group.evaluate("(el) => el.open")
        group.locator("summary").click()
        page.wait_for_function("""() => {
            const v = JSON.parse(localStorage.getItem('yb.nav.groups.v1') || '{}');
            return v.research === false;
        }""")
        page.reload()
        page.wait_for_function(READY_JS)
        assert not page.locator('details[data-group="research"]').evaluate("(el) => el.open")
        page.select_option("#langSelect", "en")
        page.wait_for_function("""() => document.querySelector(
            'details[data-group="research"] > summary').textContent === 'Research'""")
        assert not page.locator('details[data-group="research"]').evaluate("(el) => el.open")
        page.goto(f"{base_url}/#/find")
        page.wait_for_function(READY_JS)
        assert page.locator('details[data-group="research"]').evaluate("(el) => el.open")
        assert page.locator('a.nav-item[href="#/find"]').get_attribute("aria-current") == "page"
    finally:
        page.context.close()



@pytest.mark.parametrize("route,required", [
    ("help", ("YouTube Brain nedir?", "Ölçümler nasıl okunur?",
              "Sık Sorulan Sorular", "Her sayı nereden geliyor?")),
    ("mcp", ("MCP Bağlantısı", "Veri toplama", "Bağlantı kontrolü")),
])
def test_turkish_help_and_mcp_panels_use_localised_labels(browser, base_url, route, required):
    """Help and MCP documentation must be Turkish while code snippets keep their exact syntax."""
    page = _new_page(browser, "tr")
    problems = []
    page.on("pageerror", lambda error: problems.append(str(error)))
    try:
        page.goto(f"{base_url}/#/{route}")
        page.wait_for_function(READY_JS)
        page.wait_for_load_state("networkidle")
        content = page.inner_text("#view")
        assert all(text in content for text in required), (route, content[:1000])
        assert not problems, problems
        if route == "mcp":
            assert "docker compose" in content
            assert "niche-finder" in content
    finally:
        page.context.close()


def test_completed_turkish_dictionary_keys_and_placeholders(browser, base_url):
    """Fully translated namespaces keep matching keys, plurals and template fields."""
    namespaces = (
        "app", "router", "overview", "find", "viral", "ideas", "categories",
        "keywords", "shared", "channels", "tracker", "saved", "calendar", "alerts",
        "data", "tags", "language", "clusters", "titles", "packaging", "niches",
        "metadata", "transcripts", "enter", "compare", "manualRuns",
        "planState", "impersonation", "plan", "hookView",
        "ui", "account", "profile", "own", "brief", "channel", "niche",
        "admin", "mcp", "help",
    )
    page = _new_page(browser, "tr")
    try:
        page.goto(f"{base_url}/#/overview")
        page.wait_for_function(READY_JS)
        dictionaries = page.evaluate("""async names => {
            return await Promise.all(names.map(async name => {
                const en = (await import('/i18n/en/' + name + '.js')).default;
                const tr = (await import('/i18n/tr/' + name + '.js')).default;
                return { name, en, tr };
            }));
        }""", list(namespaces))
    finally:
        page.context.close()

    fields = lambda value: sorted(set(re.findall(r"\{(\w+)\}", str(value))))
    errors = []
    for entry in dictionaries:
        namespace, en, tr = entry["name"], entry["en"], entry["tr"]
        for key in set(en) ^ set(tr):
            errors.append(f"{namespace}.{key}: missing Turkish/English key")
        for key in set(en) & set(tr):
            # Dict-valued plural strings have exactly matching plural variants.
            if isinstance(en[key], dict) != isinstance(tr[key], dict):
                errors.append(f"{namespace}.{key}: different plural shape")
                continue
            if isinstance(en[key], dict) and set(en[key]) != set(tr[key]):
                errors.append(f"{namespace}.{key}: different plural keys")
            def flatten(v):
                return " ".join(str(x) for x in v.values()) if isinstance(v, dict) else str(v)
            if fields(flatten(en[key])) != fields(flatten(tr[key])):
                errors.append(f"{namespace}.{key}: mismatched template placeholders")
    assert not errors, "\n".join(sorted(errors))


def test_dictionaries_match_and_every_key_used_exists(browser, base_url):
    """У каждого неймспейса одинаковые ключи и {плейсхолдеры} в ru и en, и каждый
    t('ключ') в коде есть в словаре своего модуля."""
    i18n = ROOT / "frontend" / "i18n"
    names = sorted(p.stem for p in (i18n / "ru").glob("*.js"))
    page = _new_page(browser, "ru")
    try:
        page.goto(f"{base_url}/#/overview")
        dicts = page.evaluate("""async (names) => {
          const out = {};
          for (const ns of names) out[ns] = {
            ru: (await import(`/i18n/ru/${ns}.js`)).default,
            en: (await import(`/i18n/en/${ns}.js`)).default };
          return out;
        }""", names)
    finally:
        page.context.close()

    def flat(v):
        return " ".join(v.values()) if isinstance(v, dict) else str(v)

    errors = []
    for ns, d in dicts.items():
        for k in sorted(set(d["ru"]) ^ set(d["en"])):
            errors.append(f"{ns}.{k}: есть только в {'ru' if k in d['ru'] else 'en'}")
        for k in set(d["ru"]) & set(d["en"]):
            ph = [sorted(set(re.findall(r"\{(\w+)\}", flat(d[loc][k])))) for loc in ("ru", "en")]
            if ph[0] != ph[1]:
                errors.append(f"{ns}.{k}: плейсхолдеры ru {ph[0]} != en {ph[1]}")

    imp = re.compile(r"import\s+ru\s+from\s+'[./]*i18n/ru/(\w+)\.js'")
    for path in (ROOT / "frontend").rglob("*.js"):
        # i18n.js -- сама библиотека: в её комментарии пример импорта и t('title')
        if "i18n" in path.parts or "tests" in path.parts or path.name == "i18n.js":
            continue
        src = path.read_text(encoding="utf-8")
        m = imp.search(src)
        if not m:
            continue
        keys = dicts.get(m.group(1), {}).get("en", {})
        for key in set(re.findall(r"\bt\(\s*'(\w+)'", src)):
            if key not in keys:
                errors.append(f"{path.relative_to(ROOT).as_posix()}: t('{key}') нет в словаре {m.group(1)}")
    assert not errors, "\n".join(sorted(errors))


def test_language_switch_rerenders_without_reload(browser, base_url):
    page = _new_page(browser, "en")
    problems = []
    page.on("pageerror", lambda e: problems.append(str(e)))
    try:
        page.goto(f"{base_url}/#/overview")
        page.wait_for_function(READY_JS, timeout=30000)
        assert page.inner_text("#crumbSection") == "Overview"
        page.evaluate("window.__sameDocument = true")
        page.select_option("#langSelect", "ru")
        page.wait_for_function("() => document.querySelector('#crumbSection').textContent === 'Обзор'",
                               timeout=15000)
        state = page.evaluate("""() => ({ lang: document.documentElement.lang,
          same: window.__sameDocument === true, stored: localStorage.getItem('nf.locale'),
          nav: document.querySelector('#nav .nav-item .nav-label').textContent })""")
    finally:
        page.context.close()
    assert state == {"lang": "ru", "same": True, "stored": "ru", "nav": "Обзор"}, state
    assert not problems, problems


@pytest.mark.parametrize("route,expected", [
    # Карточка пробелов (план 03): без кэша комментариев -- кнопка «Прочитать
    # комментарии», квота сама не тратится.
    ("niche/demo", ["Пробелы в контенте", "Прочитать комментарии"]),
    # Стили превью (план 13): без векторов -- кнопка посчитать, квота не тратится.
    ("niche/demo", ["Стили превью", "Посчитать векторы превью"]),
    # Мои каналы (план 14): без OAuth-клиента -- пошаговая настройка, а не ошибка.
    ("own", ["Подключение не настроено", "OWN_TOKENS_KEY"]),
    ("own?error=access_denied", ["Подключить не удалось", "access_denied"]),
    # Сценарии MCP (план 11): раздел на экране подключения.
    ("mcp", ["Сценарии", "find_niche", "niche_health"]),
    # Тренд ниши (план 08): блок на экране ниши и колонка в списке ниш.
    ("niche/demo", ["Тренд ниши", "Видео за 30 дней"]),
    ("niches", ["Тренд"]),
    ("channel-compare/UC0000000000000000000a,UC0000000000000000000f",
     ["Сравнение каналов конкурентов", "Медиана просмотров на видео"]),
    # Что общего у выстреливших (план 29): блок на экране ниши, на демо-данных -- «мало данных».
    ("niche/demo", ["Что общего у выстреливших", "Корреляция, не причина"]),
    # Другой язык (план 26): на демо-данных -- либо выбор пары, либо подсказка собрать второй язык.
    ("language", ["Другой язык"]),
    # Где заходить (план 27): рейтинг ниш с пояснением, что веса — суждение.
    ("enter", ["Где заходить", "Веса — наше суждение", "Сравнить выбранные"]),
    # Чистая прибыль (план 30): карточка канала и ниши, редактор профилей на «Данных».
    ("channel/UC0000000000000000000a", ["Чистая прибыль", "Профиля расходов нет"]),
    # Контент-календарь (план 33): неделя и черновики без даты.
    ("calendar", ["Календарь", "Без даты", "хранится в UTC"]),
    # Партнёры для коллабораций (план 31): блок на экране канала.
    ("channel/UC0000000000000000000a", ["Партнёры для коллабораций", "контактов YouTube не даёт"]),
    ("niche/demo", ["Чистая прибыль", "Окупается с"]),
    ("data", ["Профили расходов", "Профилей пока нет"]),
    # Бриф под вопрос зрителей: тема из ?gap= доходит до экрана.
    ("brief/avid000?gap=how%20to%20start%20a%20tiny%20AI%20lab%3F",
     ["Бриф под пробел", "how to start a tiny AI lab?"]),
])
def test_content_gaps_parts_are_on_screen(browser, base_url, route, expected):
    page = _new_page(browser)
    try:
        page.goto(f"{base_url}/#/{route}")
        page.wait_for_function(READY_JS, timeout=30000)
        page.wait_for_load_state("networkidle")
        text = page.inner_text("#view")
    finally:
        page.context.close()
    # Подписи плиток и заголовки таблиц CSS выводит заглавными, inner_text
    # отдаёт уже преобразованный текст -- сравниваем без регистра.
    for part in expected:
        assert part.lower() in text.lower(), f"{part!r} not on #/{route}: {text[:400]}"


def test_sign_in_screen_when_multi_user_mode_has_no_session(browser, base_url):
    # План 15: сервер с NF_MULTI_USER=1 без сессии -- дашборд показывает вход, а не
    # сыплет ошибками 401 по экранам. Ответ /api/auth/me подменяем.
    page = _new_page(browser)
    problems = []
    page.on("pageerror", lambda e: problems.append(str(e)))
    page.route("**/api/auth/me", lambda r: r.fulfill(
        status=200, content_type="application/json", body='{"multiUser": true, "user": null}'))
    try:
        page.goto(f"{base_url}/#/overview")
        page.wait_for_selector("#signInForm", timeout=30000)
        text = page.inner_text("#view")
    finally:
        page.context.close()
    assert "Вход в YouTube Brain" in text and not problems



def test_token_section_shows_only_with_sign_in(browser, base_url):
    # План 15 (5.7-5.8): без входа раздела токенов нет, с входом -- есть.
    page = _new_page(browser)
    page.route("**/api/auth/me", lambda r: r.fulfill(status=200, content_type="application/json",
        body='{"multiUser": true, "user": {"id": 2, "email": "a@x", "isAdmin": false}, "quota": null}'))
    page.route("**/api/auth/tokens", lambda r: r.fulfill(status=200, content_type="application/json",
        body='{"tokens": [{"id": 1, "name": "ext", "createdAt": "2026-09-29T00:00:00+00:00", "lastUsedAt": null}]}'))
    try:
        page.goto(f"{base_url}/#/mcp")
        page.wait_for_selector("#apiTokens .card", timeout=30000)
        text = page.inner_text("#apiTokens")
    finally:
        page.context.close()
    assert "Личные токены" in text and "ext" in text

def test_v13_editorial_review_not_a_publication_approval(browser, base_url):
    """Use one synthetic archive result: no YouTube search or live channel access."""
    import json

    lead = {
        "profile": "kayip", "status": "research-leads",
        "relatedNiches": 1, "sampleVideos": 3, "selectedDistinctChannels": 1,
        "candidates": [{
            "videoId": "abcdefghijk", "channelId": "UC-demo", "channelTitle": "Demo",
            "referenceTitle": "Bir Osmanlı belgesi", "nicheLabel": "Osmanlı",
            "outlierScore": 3.0, "views": 4000, "vph24h": None,
            "competitionEvidence": {"sampleVideos": 3, "sampleChannels": 2},
        }],
    }
    page = _new_page(browser, "tr")
    try:
        page.route("**/api/daily-decisions*", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body=json.dumps(lead)))
        page.goto(f"{base_url}/#/brainNext")
        page.wait_for_function(READY_JS)
        page.get_by_role("button", name="Özgün fikir ve kaynak kontrolü").click()
        page.locator("#bnAngle").fill(
            "Arşiv belgelerindeki tarih anlatılarının farklı yorumlarını "
            "bağımsız belgelerle karşılaştırmak")
        page.locator("#bnEffort").select_option("medium")
        page.locator("#bnReviewSubmit").click()
        page.get_by_text("Araştırma henüz tamamlanmadı").wait_for()
        assert "En az iki farklı" in page.locator("#bnEditorialOutcome").inner_text()

        page.locator(".bn-source-url").nth(0).fill("https://arsiv.gov.tr/kaynak")
        page.locator(".bn-source-url").nth(1).fill("https://universite.edu.tr/makale")
        page.locator(".bn-source-type").nth(1).select_option("academic")
        page.locator(".bn-source-reviewed").nth(0).check()
        page.locator(".bn-source-reviewed").nth(1).check()
        page.locator("#bnClaimsReviewed").check()
        page.locator("#bnRightsReviewed").check()
        page.locator("#bnReviewSubmit").click()
        page.get_by_text("İnsan editör incelemesine hazırlanmış").wait_for()
        assert "Bu bir yayın onayı değildir." in page.locator(
            "#bnEditorialOutcome").inner_text()
        page.get_by_role("button",
                         name="Seslendirme ve sahne üretim taslağını oluştur").click()
        page.get_by_text("Video Üretim Taslağı — v14").wait_for()
        production = page.locator("#bnProductionResult").inner_text()
        assert "Kendi sesinle kayıt ve kurgu akışı" in production
        assert "Sahne storyboard iskeleti" in production
        assert "Yayın onayı: Yok" in production
        assert "AI senaryo üretimi: Yok" in production
        assert page.locator("#bnCopyProductionJson").count() == 1
        page.locator("#bnAngle").fill(
            "Düzeltilmiş araştırma açısından yeniden farklı kaynakları karşılaştırmak")
        assert page.locator("#bnProductionResult").inner_text() == ""
        assert page.locator("#bnEditorialOutcome").inner_text() == ""
    finally:
        page.context.close()

