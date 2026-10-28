/* Экран дашборда. Роутинг -- router.js, общее -- shared.js, компоненты -- ui.js. */
import { $, api, q, num, esc, toast, tile, sectionHead, notice, state } from '../ui.js';
import { view, plabel, collectForm, wireCollect, render } from '../shared.js';
import { manualRunStatus, manualRunAvailable, wireManualRun } from '../manual-runs.js';
import { dict, fmtDate } from '../i18n.js';
import ru from '../i18n/ru/data.js';
import en from '../i18n/en/data.js';
import tr from '../i18n/tr/data.js';

const t = dict({ ru, en, tr });

/* ----------------------------------------------------------------- Данные */

async function viewData() {
  const [h, cov, fresh, runs, discovery] = await Promise.all([
    api('/api/health'), api(`/api/coverage${q({ period: state.period })}`),
    api('/api/freshness').catch(() => null), manualRunStatus(),
    api('/api/discovery-activity').catch(() => null)]);
  view.innerHTML = `
    ${h.hasApiKey ? notice(t('apiKeyOk'), 'ok')
                  : notice(t('apiKeyMissing'), 'error')}
    ${h.historyAvailable ? '' : notice(t('noHistory'))}
    <div class="card">
      ${sectionHead(t('dbTitle'), h.db.db_path)}
      <div class="tiles">
        ${tile(t('tileChannels'), num(h.db.channels))}
        ${tile(t('tileVideos'), num(h.db.videos))}
        ${tile(t('tileNiches'), num(h.db.niches))}
        ${tile(t('tileVideoSnapshots'), num(h.db.video_stat_snapshots))}
        ${tile(t('tileChannelSnapshots'), num(h.db.channel_stat_snapshots))}
        ${tile(t('tilePackagingChanges'), num(h.db.title_thumbnail_changes))}
        ${tile(t('tileInWindow'), num(cov.videosPublishedInPeriod), plabel(state.period))}
      </div>
    </div>
    ${freshnessCard(fresh)}
    ${discoveryActivityCard(discovery)}
    <div id="costProfiles"></div>
    ${collectForm()}
    ${manualRunAvailable(runs, 'refresh') ? `<div class="card">
      ${sectionHead(t('refreshTitle'), runs.admin ? t('refreshSub') : t('refreshSubMine'))}
      <button class="btn btn-ghost" id="refreshBtn" type="button">${t('refreshNow')}</button>
    </div>` : ''}`;
  wireCollect(render);
  loadNotifySettings();
  loadCostProfiles();
  // P2-11: админ обновляет корпус, пользователь с лимитом -- свои каналы
  const btn = $('#refreshBtn');
  if (btn) {
    wireManualRun(btn, runs, 'refresh', t('refreshNow'), async () => {
      const r = await api('/api/refresh', { method: 'POST', body: { period: '30d' } });
      toast(t('refreshed', { videos: r.videos.refreshed, channels: r.channels.refreshed }), 'ok');
      render();
    });
  }
}

/* Scheduler metadata is not evidence that a YouTube search succeeded. */
function discoveryActivityCard(activity) {
  if (!activity) return '';
  const status = (entry) => ({
    recent: t('discoveryMarkerRecent'),
    stale: t('discoveryMarkerStale'),
    clock_skew: t('discoveryMarkerFuture'),
    invalid: t('discoveryMarkerInvalid'),
    missing: t('discoveryMarkerMissing'),
  }[entry?.state] || t('discoveryMarkerMissing'));
  const stamp = (entry) => entry?.at ? esc(fmtDate(entry.at)) : '—';
  return `<div class="card">
    ${sectionHead(t('discoveryActivityTitle'), t('discoveryActivitySub'))}
    <div class="tiles">
      ${tile(t('discoveryDailyMarker'), stamp(activity.dailySchedulerMarker),
              status(activity.dailySchedulerMarker))}
      ${tile(t('discoveryTopicMarker'), stamp(activity.topicSchedulerMarker),
              status(activity.topicSchedulerMarker))}
      ${tile(t('discoverySearchToday'), num(activity.searchQuota.callsToday),
              t('discoverySearchRemaining', { count: num(activity.searchQuota.callsLeft) }))}
      ${tile(t('discoveryUnitsToday'), num(activity.unitQuota.unitsToday),
              t('discoveryUnitsRemaining', { count: num(activity.unitQuota.unitsLeft) }))}
    </div>
    <div class="section-sub" style="margin-top:10px">
      ${activity.searchQuota.callsToday === 0 ? t('discoveryNoSearchToday') + ' ' : ''}
      ${t('discoveryEvidenceWarning')}
    </div>
    ${discoveryRunCard(activity.discoveryRun)}
    ${topicSearchRunCard(activity.topicSearchRun)}
  </div>`;
}



function discoveryRunCard(run) {
  if (!run) return `<div class="section-sub" style="margin-top:12px">
    ${t('discoveryRunMissing')}</div>`;
  const time = run.recorded?.at ? esc(fmtDate(run.recorded.at)) : '—';
  const freshness = run.recorded?.state === 'recent'
    ? t('discoveryMarkerRecent') : t('discoveryMarkerStale');
  return `<div class="section-sub" style="margin-top:12px">
    ${sectionHead(t('discoveryLastRunTitle'), time + ' · ' + freshness)}
    <div class="tiles">
      ${tile(t('discoveryQueriesConfigured'), num(run.configuredTopics))}
      ${tile(t('discoveryQueriesSucceeded'), num(run.successful))}
      ${tile(t('discoveryQueriesFailed'), num(run.failed + run.invalidResults))}
      ${tile(t('discoveryQueriesQuotaBlocked'), num(run.quotaBlocked))}
      ${tile(t('discoveryQueriesSkipped'), num(run.skipped))}
      ${tile(t('discoveryVideosFound'), num(run.videosFound))}
      ${tile(t('discoveryVideosProcessed'), num(run.videosProcessed))}
      ${tile(t('discoveryChannelProfiles'), num(run.channelProfilesReported))}
    </div>
    <div class="section-sub" style="margin-top:10px">
      ${run.configuredTopics === 0 ? t('discoveryQueriesNotConfigured') + ' ' : ''}
      ${t('discoveryOutcomeWarning')}
    </div>
  </div>`;
}



function topicSearchRunCard(run) {
  if (!run) return `<div class="section-sub" style="margin-top:12px">
    ${t('discoveryTopicRunMissing')}</div>`;
  const time = run.recorded?.at ? esc(fmtDate(run.recorded.at)) : '—';
  const status = {
    ok: t('discoveryTopicRunOk'),
    failed: t('discoveryTopicRunFailed'),
    quota: t('discoveryTopicRunQuota'),
    skipped: t('discoveryTopicRunSkipped'),
    invalid_result: t('discoveryTopicRunInvalid'),
  }[run.state] || t('discoveryTopicRunInvalid');
  return `<div class="section-sub" style="margin-top:14px">
    <strong>${t('discoveryTopicRunTitle')}</strong> · ${time} · ${status}
    <div class="tiles">
      ${tile(t('discoveryTopicsSearched'), num(run.topicsSearched))}
      ${tile(t('discoveryTopicNewVideos'), num(run.videosStored))}
      ${tile(t('discoveryTopicSearchCalls'), num(run.searchCalls))}
    </div>
    <div class="section-sub" style="margin-top:8px">
      ${t('discoveryTopicEvidenceWarning')}
    </div>
  </div>`;
}


/* План 30: профили расходов -- сколько стоит сделать одно видео (озвучка, монтаж,
   ИИ-генерация, стоки) и постоянные расходы в месяц. Личные: у каждого свои. */
async function loadCostProfiles() {
  const box = $('#costProfiles');
  if (!box) return;
  let profiles = [];
  try { profiles = (await api('/api/cost-profiles')).profiles; } catch { return; }
  const field = (id, label, value = '') => `<label class="field-label">${label}<br>
    <input type="number" min="0" step="0.01" id="${id}" value="${esc(value)}" style="width:110px"></label>`;
  box.innerHTML = `<div class="card">
    ${sectionHead(t('costTitle'), t('costSub'))}
    ${profiles.length ? `<div class="table-wrap"><table><thead><tr><th>${t('colProfile')}</th><th class="num">${t('colPerVideo')}</th>
      <th class="num">${t('colPerMinute')}</th><th class="num">${t('colMonthly')}</th><th></th></tr></thead><tbody>${profiles.map((p) => `<tr>
        <td>${esc(p.name)}</td><td class="num">$${p.per_video_usd}</td><td class="num">$${p.per_minute_usd}</td>
        <td class="num">$${p.monthly_usd}</td>
        <td class="num"><button class="btn btn-ghost btn-sm js-cp-edit" data-id="${p.id}">${t('edit')}</button>
          <button class="btn btn-ghost btn-sm js-cp-del" data-id="${p.id}">${t('del')}</button></td></tr>`).join('')}</tbody></table></div>`
      : `<div class="section-sub">${t('costEmpty')}</div>`}
    <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin-top:12px">
      <label class="field-label">${t('fieldName')}<br><input type="text" id="cpName" placeholder="${esc(t('namePlaceholder'))}" style="width:200px"></label>
      ${field('cpVideo', t('fieldPerVideo'))}${field('cpMinute', t('fieldPerMinute'))}${field('cpMonth', t('fieldMonthly'))}
      <button class="btn" id="cpSave">${t('save')}</button>
    </div>
    <div class="section-sub" style="margin-top:6px">${t('costExample')}</div></div>`;
  let editing = null;
  box.querySelectorAll('.js-cp-edit').forEach((b) => b.addEventListener('click', () => {
    const p = profiles.find((x) => String(x.id) === b.dataset.id);
    editing = p.id;
    $('#cpName').value = p.name; $('#cpVideo').value = p.per_video_usd;
    $('#cpMinute').value = p.per_minute_usd; $('#cpMonth').value = p.monthly_usd;
  }));
  box.querySelectorAll('.js-cp-del').forEach((b) => b.addEventListener('click', async () => {
    try { await api(`/api/cost-profiles/${b.dataset.id}`, { method: 'DELETE' }); loadCostProfiles(); }
    catch (e) { toast(e.message, 'err'); }
  }));
  $('#cpSave').addEventListener('click', async () => {
    try {
      await api('/api/cost-profiles', { method: 'POST', body: { id: editing, name: $('#cpName').value,
        perVideoUsd: $('#cpVideo').value, perMinuteUsd: $('#cpMinute').value, monthlyUsd: $('#cpMonth').value } });
      toast(t('profileSaved'), 'ok');
      loadCostProfiles();
    } catch (e) { toast(e.message, 'err'); }
  });
}

/* План 16: правило YouTube API (III.E.4) — данные, полученные по ключу, хранить
   не дольше 30 дней без обновления. Воркер раз в сутки перечитывает самые старые
   строки; ничего не удаляется (решение владельца) — история остаётся на его риске. */
function freshnessCard(f) {
  if (!f) return '';
  const day = (iso) => (iso ? fmtDate(iso) : '—');
  return `<div class="card">
      ${sectionHead(t('freshnessTitle'), t('freshnessSub'))}
      <div class="tiles">
        ${tile(t('tileStaleVideos'), num(f.videos.stale), t('staleNote', { days: f.staleDays, total: num(f.videos.total) }))}
        ${tile(t('tileStaleChannels'), num(f.channels.stale), t('staleNote', { days: f.staleDays, total: num(f.channels.total) }))}
        ${tile(t('tileHistorySince'), day(f.historySince))}
      </div>
      <div class="section-sub" style="margin-top:10px">${t('freshnessNote', {
        videos: num(f.dailyCap.videos), channels: num(f.dailyCap.channels) })}</div>
    </div>`;
}

/* План 15 (5.9): свои уведомления -- Telegram или webhook и режим. Секреты
   уходят на сервер один раз и обратно не показываются. Без сохранённых
   настроек у локального пользователя работают NOTIFY_* из .env. */
async function loadNotifySettings() {
  let st;
  try { st = await api('/api/settings/notifications'); } catch { return; }
  const box = document.createElement('div');
  box.className = 'card';
  box.id = 'notifyCard';
  const src = { env: t('srcEnv'), settings: t('srcSettings'), none: t('srcNone') }[st.source] || st.source;
  box.innerHTML = `${sectionHead(t('notifyTitle'), t('notifySub', {
      source: esc(src), telegram: st.telegram ? t('yes') : t('no'),
      webhook: st.webhook ? t('yes') : t('no'), mode: esc(st.mode) }))}
    <div style="display:grid;gap:8px;max-width:520px">
      <input type="password" id="nfBot" placeholder="${st.telegram ? t('botSaved') : t('botPlaceholder')}" autocomplete="off">
      <input type="text" id="nfChat" placeholder="chat id" value="${esc(st.telegramChatId || '')}">
      <input type="password" id="nfHook" placeholder="${st.webhook ? t('hookSaved') : t('hookPlaceholder')}" autocomplete="off">
      <select id="nfMode">${['instant', 'digest', 'both', 'off'].map((m) =>
        `<option value="${m}"${m === st.mode ? ' selected' : ''}>${{ instant: t('modeInstant'), digest: t('modeDigest'), both: t('modeBoth'), off: t('modeOff') }[m]}</option>`).join('')}</select>
      <div><button class="btn btn-sm" id="nfSave" type="button">${t('save')}</button>
        <button class="btn btn-ghost btn-sm" id="nfTest" type="button">${t('testMessage')}</button>
        ${st.source === 'settings' ? `<button class="btn btn-ghost btn-sm" id="nfClear" type="button">${t('reset')}</button>` : ''}</div>
    </div>
    <div class="section-sub">${t('notifyNote')}</div>`;
  view.appendChild(box);
  const body = () => {
    const b = { telegramChatId: $('#nfChat').value, mode: $('#nfMode').value };
    if ($('#nfBot').value.trim()) b.telegramBotToken = $('#nfBot').value.trim();
    if ($('#nfHook').value.trim()) b.webhookUrl = $('#nfHook').value.trim();
    return b;
  };
  $('#nfSave').addEventListener('click', async () => {
    try { await api('/api/settings/notifications', { method: 'PUT', body: body() }); toast(t('saved'), 'ok'); box.remove(); loadNotifySettings(); }
    catch (e) { toast(e.message, 'err'); }
  });
  $('#nfTest').addEventListener('click', async () => {
    try { const r = await api('/api/settings/notifications/test', { method: 'POST' }); toast(r.sent ? t('sent') : t('notSent'), r.sent ? 'ok' : 'err'); }
    catch (e) { toast(e.message, 'err'); }
  });
  const clear = $('#nfClear');
  if (clear) clear.addEventListener('click', async () => {
    try { await api('/api/settings/notifications', { method: 'PUT', body: { clear: true } }); box.remove(); loadNotifySettings(); }
    catch (e) { toast(e.message, 'err'); }
  });
}

export { viewData };
