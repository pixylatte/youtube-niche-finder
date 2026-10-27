/* YouTube Brain Next v0.1 — channel-labelled editorial research.
 * No claim of a verified channel connection. This screen queries the existing
 * local corpus via /api/ideas/check; it does not call YouTube or spend search quota.
 */
import { $, api, esc, toast, state } from '../ui.js';
import { view } from '../shared.js';

const CHANNELS = {
  kayip: {
    name: 'Kayıp Sayfalar',
    subjects: [
      'Göbeklitepe\'nin bilinmeyen yönleri',
      'Antikythera mekanizmasının gizemi',
      'Çatalhöyük\'te yaşam',
      'Tarihte kaybolan şehirler',
      'İstanbul\'un fethinde kuşatma teknolojileri',
    ],
  },
  islam: {
    name: '1 Dakika İslam',
    subjects: [
      'Hicretin önemi',
      'İnfak nedir?',
      'Sabır hakkında hadisler',
      'Zekât kimlere verilir?',
      'Güzel ahlakın önemi',
    ],
  },
};

let channel = localStorage.getItem('ybnext.channel') === 'islam' ? 'islam' : 'kayip';
const drafts = {};
const checked = {};
let checkedFor = null;
let lastNiche = '';

function initialText(key) {
  return drafts[key] ?? CHANNELS[key].subjects.join('\n');
}

function positiveEvidence(item) {
  return item && item.verdict === 'proven' && Number(item.matchCount) > 0;
}

function orderedResults(payload) {
  const items = Array.isArray(payload?.ideas) ? payload.ideas : [];
  const priority = { proven: 0, recent: 1, free: 2, flopped: 3 };
  return items.slice().sort((a, b) => {
    const ap = priority[a.verdict] ?? 4;
    const bp = priority[b.verdict] ?? 4;
    if (ap !== bp) return ap - bp;
    const ae = Number(a.bestOutlierScore) || 0;
    const be = Number(b.bestOutlierScore) || 0;
    return be - ae;
  });
}

function verdictText(item) {
  switch (item.verdict) {
    case 'proven': return 'Toplanan veride talep sinyali var';
    case 'recent': return 'Yakın zamanda işlenmiş';
    case 'flopped': return 'Zayıf performans sinyali';
    default: return 'Yeterli kanıt bulunamadı';
  }
}

function sources(item) {
  const videos = Array.isArray(item.matches) ? item.matches.slice(0,3) : [];
  if (!videos.length) return '<p class="section-sub">Bu fikir için eşleşen video kanıtı yok.</p>';
  return '<ul style="padding-left:18px;margin:10px 0">' + videos.map((m) => {
    const id = String(m.videoId || '');
    if (!/^[a-zA-Z0-9_-]{6,20}$/.test(id)) return '';
    const title = esc(m.title || id);
    const creator = esc(m.channelTitle || m.channelId || '');
    return `<li><a target="_blank" rel="noopener noreferrer" href="https://www.youtube.com/watch?v=${encodeURIComponent(id)}">${title}</a> <span class="section-sub">— ${creator}</span></li>`;
  }).join('') + '</ul>';
}

function resultsHtml(key, niche) {
  const payload = checked[key];
  if (!payload || checkedFor !== key || lastNiche !== niche) return '';
  const all = orderedResults(payload);
  const backed = all.filter(positiveEvidence).slice(0,3);
  const remaining = all.filter((x) => !backed.includes(x));
  const card = (item) => `<div class="card">
    <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap">
      <strong>${esc(item.idea || '')}</strong>
      <span class="chip ${positiveEvidence(item) ? 'chip-good' : ''}">${esc(verdictText(item))}</span>
    </div>
    <p class="section-sub" style="margin-top:8px">
      Eşleşen video: ${Number(item.matchCount) || 0}
      ${Number.isFinite(Number(item.bestOutlierScore)) && Number(item.matchCount) > 0
        ? ` · En yüksek outlier: ×${Number(item.bestOutlierScore).toFixed(1)}` : ''}
    </p>
    ${sources(item)}
  </div>`;

  return `<div class="card">
    <h2>Veriye dayalı inceleme listesi</h2>
    <p class="section-sub">Kaynak: Niche Finder yerel video arşivi ve fikir kontrolü.
    Bu sıralama bir başarı garantisi veya gerçek zamanlı YouTube trend listesi değildir.
    Kapsam: ${niche ? esc(niche) : 'toplanan bütün nişler'}.</p>
    ${backed.length ? `<p><strong>${backed.length} kanıtlı araştırma adayı</strong> — en fazla üç fikir gösteriliyor.</p>`
      : '<p class="section-sub">Henüz doğrulanmış talep sinyali yok. Yeni konu toplama veya rakip verisi gerekli.</p>'}
  </div>
  ${backed.map(card).join('')}
  ${remaining.length ? `<div class="card"><h3>Diğer fikirler — kesin öneri değil</h3>
    <p class="section-sub">Aşağıdakiler yakın zamanda işlenmiş, zayıf ya da mevcut veriyle doğrulanamamış konular.</p>
    </div>${remaining.map(card).join('')}` : ''}
  ${!all.length ? '<div class="card">Yerel arşiv bu fikirler için sonuç döndürmedi.</div>' : ''}`;
}

function viewBrainNext() {
  const key = channel;
  const niche = state.niche || '';
  const name = CHANNELS[key].name;
  view.innerHTML = `<div class="card">
    <h1>YouTube Brain Next <span class="chip">v0.1</span></h1>
    <h2>Günlük Video Karar Merkezi</h2>
    <p class="section-sub">Kanal çalışma profili seç, fikirlerini mevcut arşivde kontrol et,
      kararını video kanıtlarına göre ver. Bunlar örnek araştırma başlıklarıdır;
      kanal hesapların henüz bağlanmış sayılmaz.</p>
    <div class="form-row">
      <label class="field"><span class="field-label">Kanal çalışma profili</span>
        <select id="bnChannel">
          ${Object.entries(CHANNELS).map(([id, p]) =>
            `<option value="${id}" ${key === id ? 'selected' : ''}>${esc(p.name)}</option>`).join('')}
        </select>
      </label>
      <div class="field"><span class="field-label">Korpus niş filtresi</span>
        <div class="section-sub" style="padding:10px 0">${niche ? esc(niche) : 'Tüm toplanan nişler'}</div>
      </div>
    </div>
    <label class="field" for="bnIdeas"><span class="field-label">${esc(name)} için incelenecek fikirler (satır başına bir konu)</span></label>
    <textarea id="bnIdeas" rows="7" maxlength="2400" style="width:100%;resize:vertical;font-family:inherit"
      placeholder="Her satıra bir konu yaz">${esc(initialText(key))}</textarea>
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px">
      <button class="btn" type="button" id="bnCheck">Mevcut verilerle karşılaştır</button>
      <a class="btn btn-ghost" href="#/ideas">Ayrıntılı fikir kontrolü</a>
      <a class="btn btn-ghost" href="#/data">Veri toplama</a>
    </div>
    <p class="section-sub" style="margin-top:12px">Bu işlem yalnız mevcut veritabanındaki videoları kontrol eder;
      YouTube API'den yeni veri çekmez. Fikirlerin doğrulanması için ilgili niş ve rakip verisinin toplanması gerekir.</p>
  </div>
  ${resultsHtml(key, niche)}`;

  $('#bnChannel').addEventListener('change', (event) => {
    drafts[channel] = $('#bnIdeas').value;
    channel = event.target.value === 'islam' ? 'islam' : 'kayip';
    localStorage.setItem('ybnext.channel', channel);
    viewBrainNext();
  });

  $('#bnIdeas').addEventListener('input', (event) => {
    drafts[key] = event.target.value;
    checkedFor = null;
  });

  $('#bnCheck').addEventListener('click', async () => {
    const ideas = [...new Set($('#bnIdeas').value.split('\n').map((x) => x.trim()).filter(Boolean))].slice(0,12);
    if (!ideas.length) { toast('En az bir video fikri gir.', 'err'); return; }
    const btn = $('#bnCheck');
    btn.disabled = true;
    btn.textContent = 'Karşılaştırılıyor…';
    try {
      const result = await api('/api/ideas/check', { method: 'POST', body: {
        ideas, niche: niche || undefined, recentDays: 90,
        provenOutlier: 2.0, flopOutlier: 0.5,
      }});
      checked[key] = result;
      checkedFor = key;
      lastNiche = niche;
      drafts[key] = $('#bnIdeas')?.value || ideas.join('\n');
      if (location.hash.startsWith('#/brain-next')) viewBrainNext();
    } catch (error) {
      toast(error.message, 'err');
      btn.disabled = false;
      btn.textContent = 'Mevcut verilerle karşılaştır';
    }
  });
}

export { viewBrainNext, orderedResults, positiveEvidence };
