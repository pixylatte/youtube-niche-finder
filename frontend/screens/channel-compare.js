/* Side-by-side competitor research from existing read-only channel endpoints.
   This screen never triggers collection, embedding, LLM, or YouTube API calls. */
import { api, q, num, compact, esc, sectionHead, empty, notice, state } from '../ui.js';
import { view } from '../shared.js';
import { dict } from '../i18n.js';
import { normalizeChannelIds } from '../channel-compare-utils.js';
import ru from '../i18n/ru/channelCompare.js';
import en from '../i18n/en/channelCompare.js';
import tr from '../i18n/tr/channelCompare.js';

const t = dict({ ru, en, tr });
const plain = (v) => typeof v === 'number' && Number.isFinite(v) ? num(v) : '—';
const short = (v) => typeof v === 'number' && Number.isFinite(v) ? compact(v) : '—';
const decimal = (v) => typeof v === 'number' && Number.isFinite(v) ? v.toFixed(2) : '—';
const percent = (v) => typeof v === 'number' && Number.isFinite(v) ? `${v.toFixed(1)}%` : '—';

function metrics() {
  return [
    { label: t('metricSubscribers'), format: short, get: (x) => x.profile?.subscribers },
    { label: t('metricChannelVideos'), format: plain, get: (x) => x.profile?.videoCount },
    { label: t('metricCollectedVideos'), format: plain, get: (x) => x.performance?.videosAnalysed },
    { label: t('metricMedianViews'), format: short, get: (x) => x.performance?.medianViewsPerVideo },
    { label: t('metricMedianViewsPerSub'), format: decimal, get: (x) => x.performance?.medianViewsPerSubscriber },
    { label: t('metricViralSkew'), format: decimal, get: (x) => x.performance?.viralSkew },
    { label: t('metricBestOutlier'), format: decimal, get: (x) => x.topOutliers?.[0]?.outlierScore },
    { label: t('metricUploadsInPeriod'), format: plain, get: (x) => x.cadence?.uploadsInPeriod },
    { label: t('metricUploadsWeek'), format: decimal, get: (x) => x.cadence?.uploadsPerWeekLifetime },
    { label: t('metricShortsShare'), format: percent, get: (x) => x.cadence?.shortsSharePercent },
    { label: t('metricSnapshots'), format: plain, get: (x) => x.snapshots },
    { label: t('metricSubsGrowth30'), format: plain, get: (x) => x.growth?.['30d']?.subscribers?.per_day },
    { label: t('metricViewsGrowth30'), format: short, get: (x) => x.growth?.['30d']?.views?.per_day },
  ];
}

function comparisonTable(found) {
  return `<div class="table-wrap channel-compare-table"><table>
    <thead><tr><th scope="col">${esc(t('metric'))}</th>
      ${found.map(({id, data}) =>
        `<th scope="col"><a href="#/channel/${esc(id)}">${esc(data.profile?.title || id)}</a>
          <div class="section-sub">${esc(id)}</div></th>`).join('')}
    </tr></thead>
    <tbody>${metrics().map((row) => `<tr><th scope="row">${esc(row.label)}</th>
      ${found.map(({data}) => `<td class="num">${esc(row.format(row.get(data)))}</td>`).join('')}
    </tr>`).join('')}</tbody>
  </table></div>`;
}

async function viewChannelCompare(raw) {
  const ids = normalizeChannelIds(raw);
  if (ids.length < 2) {
    view.innerHTML = `<div class="card">${sectionHead(t('title'))}${empty(t('selectTwo'))}
      <a class="btn btn-ghost" href="#/channels">${esc(t('back'))}</a></div>`;
    return;
  }
  // Each request uses already-collected channel analytics, not live YouTube.
  // One missing/private local channel must not hide the others.
  const results = await Promise.all(ids.map(async (id) => {
    try { return { id, data: await api(`/api/channels/${encodeURIComponent(id)}${q({ period: state.period })}`) }; }
    catch { return { id, data: null }; }
  }));
  const found = results.filter((r) => r.data?.found !== false && r.data?.profile);
  const missing = results.filter((r) => !r.data?.profile).map((r) => r.id);
  view.innerHTML = `<div class="card">
    ${sectionHead(t('title'), t('sub'), `<a class="btn btn-ghost btn-sm" href="#/channels">${esc(t('back'))}</a>`)}
    ${notice(esc(t('limitations')))}
    ${missing.length ? notice(esc(t('missing', { ids: missing.join(', ') })), 'warn') : ''}
    ${found.length ? comparisonTable(found) : empty(t('noData'))}
    <div class="section-sub channel-compare-note">${esc(t('periodNote', { period: state.period }))}</div>
  </div>`;
}

export { viewChannelCompare };
