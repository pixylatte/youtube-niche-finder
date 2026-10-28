/* Экран дашборда. Роутинг -- router.js, общее -- shared.js, компоненты -- ui.js. */
import { $, api, q, num, esc, sectionHead, empty, channelRow, state, yppSelect, table, toast } from '../ui.js';
import { view, plabel, base, render } from '../shared.js';
import { dict } from '../i18n.js';
import { rivalSnapshot, parseRivalBasket } from '../rival-workbench.js';
import { representativeVideos, repeatabilityEvidence } from '../rival-formats.js';
import ru from '../i18n/ru/channels.js';
import en from '../i18n/en/channels.js';
import tr from '../i18n/tr/channels.js';

const t = dict({ ru, en, tr });

/* Research-only rivals workbench: up to three archived channels, no live search. */
const RIVALS_KEY = 'yb.rival.workbench.v1';
let rivalBasket = null;

function getRivals() {
  // A channel detail page may add a rival without a full reload.
  try { rivalBasket = parseRivalBasket(localStorage.getItem(RIVALS_KEY)); }
  catch { if (rivalBasket === null) rivalBasket = []; }
  return rivalBasket;
}

function saveRivals(ids) {
  rivalBasket = ids.slice(0, 3);
  try { localStorage.setItem(RIVALS_KEY, JSON.stringify(rivalBasket)); }
  catch { /* Browsing without storage is supported. */ }
}

function metricValue(entry, metric, format) {
  const v = entry?.[metric];
  if (v == null) return '—';
  const precise = (n) => new Intl.NumberFormat(document.documentElement.lang || 'tr', {
    maximumFractionDigits: 1,
  }).format(n);
  if (format === 'pct') return `${precise(v)}%`;
  if (format === 'mult') return `×${precise(v)}`;
  if (format === 'decimal') return precise(v);
  return num(v);
}

function rivalComparisonCard(ids, results) {
  const resolved = results.map((r, i) => {
    const data = r.status === 'fulfilled' && r.value?.found !== false
      ? rivalSnapshot(r.value) : null;
    return { id: ids[i], data };
  });
  const missing = resolved.filter((r) => !r.data).length;
  const representatives = representativeVideos(ids, results);
  const reviewable = representatives.filter((item) => item.videoId).length;
  const period = plabel(state.period);
  const columns = [
    { label: t('compareMetric'), wrap: true, render: (r) => esc(r.label) },
    ...resolved.map(({ id, data }) => ({
      label: data?.title ? data.title : id, num: true,
      render: (r) => metricValue(data, r.key, r.format),
    })),
  ];
  const entries = [
    ['subscribers', 'compareSubscribers'],
    ['reportedVideos', 'compareReported'],
    ['analysedVideos', 'compareAnalysed'],
    ['archivePercent', 'compareArchivePct', 'pct'],
    ['uploadsInPeriod', 'comparePeriodUploads'],
    ['lifetimeUploadsWeekly', 'compareWeekly', 'decimal'],
    ['shortsCount', 'compareShorts'],
    ['longformCount', 'compareLongform'],
    ['shortsShare', 'compareShortsShare', 'pct'],
    ['shortsMedianViews', 'compareShortsMedian'],
    ['longformMedianViews', 'compareLongMedian'],
    ['medianViews', 'compareMedian'],
    ['viewsPerDay30d', 'compareViewsDay', 'decimal'],
    ['subscribersPerDay30d', 'compareSubsDay', 'decimal'],
    ['bestOutlier', 'compareBestOutlier', 'mult'],
    ['snapshots', 'compareSnapshots'],
  ];
  const rows = entries.map(([key, label, format]) => ({
    key, label: label === 'comparePeriodUploads'
      ? t(label, { period }) : t(label), format,
  }));
  return `<div class="card rival-comparison-card">
    ${sectionHead(t('compareTitle'), t('compareSub'))}
    ${missing ? `<p class="rival-notice" role="status">${esc(t('compareMissing', { n: missing }))}</p>` : ''}
    <div class="rival-matrix">${table(columns, rows)}</div>
    <p class="rival-caveat">${esc(t('compareCaveat'))}</p>
    <div class="rival-profile-links">${resolved.map(({ id, data }) =>
      `<a class="btn btn-ghost btn-sm" href="#/channel/${encodeURIComponent(id)}">${esc(data?.title || id)}</a>`).join('')}</div>
    <div class="rival-format-actions">
      <div class="section-sub">${esc(t('formatReviewSub'))}</div>
      <button class="btn btn-ghost" type="button" id="rivalFormatsBtn"
        ${reviewable ? '' : 'disabled'}>${esc(t('formatReviewAction', { n: reviewable }))}</button>
    </div>
    <div id="rivalFormatResults" aria-live="polite"></div>
  </div>`;
}

/* Repeatability verdicts come from the existing domain/repeatability.py:
   >=5 matched videos from >=3 OTHER channels; "repeatable" requires
   >=3 independent channels with an outlier >=x2. Source samples only the
   strongest LONG video from each compared channel. No score extrapolation. */
function rivalFormatReport(representatives, responses) {
  const formatLabels = {
    repeatable: ['formatRepeatable', 'chip-good'],
    mixed: ['formatMixed', 'chip-warn'],
    one_off: ['formatOneOff', ''],
    unknown: ['formatUnknown', ''],
  };
  const count = (n) => n == null ? '—' : num(n);
  const cards = representatives.map((source, i) => {
    if (!source.videoId) return `<article class="rival-format-entry">
      <h3>${esc(source.channelTitle)}</h3>
      <p class="rival-format-note">${esc(t('formatNoSource'))}</p>
    </article>`;
    const result = responses[i];
    const hasResult = result?.status === 'fulfilled';
    const facts = hasResult ? repeatabilityEvidence(result.value) : null;
    const [label, cls] = facts
      ? formatLabels[facts.verdict] : ['formatError', ''];
    const detail = facts?.reason === 'no-embedding' ? t('formatNoVectors')
      : facts?.verdict === 'unknown' ? t('formatInsufficient')
      : facts ? t('formatEvidenceLine', {
        hit: count(facts.hitChannels),
        channels: count(facts.independentChannels),
        videos: count(facts.similarVideos),
      }) : t('formatRequestFailed');
    const examples = facts?.examples?.length
      ? `<ul class="rival-format-examples">${facts.examples.map((m) =>
        `<li><a href="https://www.youtube.com/watch?v=${encodeURIComponent(m.videoId)}"
            target="_blank" rel="noopener">${esc(m.title)}</a>
          ${m.channelTitle ? `<span>${esc(m.channelTitle)}</span>` : ''}
          ${m.outlierScore != null ? `<span>×${num(m.outlierScore)}</span>` : ''}
        </li>`).join('')}</ul>` : '';
    return `<article class="rival-format-entry">
      <h3>${esc(source.channelTitle)}</h3>
      <a class="rival-format-source" href="https://www.youtube.com/watch?v=${encodeURIComponent(source.videoId)}"
        target="_blank" rel="noopener">${esc(source.title || source.videoId)}</a>
      <div class="rival-format-topline">
        <span class="chip ${cls}">${esc(t(label))}</span>
        ${source.outlierScore != null
          ? `<span class="section-sub">${esc(t('formatSourceMultiplier', { x: source.outlierScore }))}</span>` : ''}
      </div>
      <p class="rival-format-note">${esc(detail)}</p>
      ${examples}
      <a class="btn btn-ghost btn-sm" href="#/brief/${encodeURIComponent(source.videoId)}">
        ${esc(t('formatOpenBrief'))}</a>
    </article>`;
  });
  return `<div class="rival-format-report">
    ${sectionHead(t('formatReportTitle'), t('formatReportSub'))}
    <div class="rival-format-grid">${cards.join('')}</div>
    <p class="rival-caveat">${esc(t('formatCaveat'))}</p>
  </div>`;
}

/* --------------------------------------------------------- Outlier-каналы */

async function viewChannels() {
  const p = Object.assign(
    { min_multiplier: 1.5, min_subscribers: '', max_subscribers: '', min_ypp_status: '' },
    JSON.parse(localStorage.getItem('nf.channels') || '{}'));
  const d = await api(`/api/outlier-channels${q({
    ...base(), min_multiplier: p.min_multiplier,
    min_subscribers: p.min_subscribers || null, max_subscribers: p.max_subscribers || null,
    min_ypp_status: p.min_ypp_status || null, limit: 50,
  })}`);
  const selected = getRivals();
  const choiceRow = (c) => {
    const id = c.channelId || '';
    const valid = /^UC[A-Za-z0-9_-]{10,40}$/.test(id);
    return `<div class="rival-choice">
      <label class="rival-choice-check"><input class="rival-check" type="checkbox"
        data-channel-id="${esc(id)}"
        aria-label="${esc(t('compareChoose', { title: c.channelTitle || id }))}"
        ${selected.includes(id) ? 'checked' : ''} ${valid ? '' : 'disabled'}>
      </label>
      ${channelRow(c)}
    </div>`;
  };
  view.innerHTML = `
    <div class="card">
      ${sectionHead(t('title'), t('sub', { period: plabel(state.period) }))}
      <div class="form-row">
        <label class="field"><span class="field-label">${t('minMultiplier')}</span>
          <input type="number" id="fcMult" value="${p.min_multiplier}" step="0.5"></label>
        <label class="field"><span class="field-label">${t('minSubs')}</span>
          <input type="number" id="fcMinSubs" value="${p.min_subscribers}" step="1000"></label>
        <label class="field"><span class="field-label">${t('maxSubs')}</span>
          <input type="number" id="fcMaxSubs" value="${p.max_subscribers}" step="1000"></label>
        ${yppSelect('fcYpp', p.min_ypp_status)}
        <button class="btn" id="applyChannels" type="button">${t('apply')}</button>
      </div>
      <div class="section-sub" style="margin-top:10px">${t('note')}</div>
    </div>
    <div class="card rival-picker">
      ${sectionHead(t('comparePickerTitle'), t('comparePickerSub'))}
      <div class="rival-picker-actions">
        <span id="rivalSelectedCount" class="section-sub" role="status"></span>
        <button class="btn" type="button" id="rivalCompareBtn">${esc(t('compareAction'))}</button>
        <button class="btn btn-ghost" type="button" id="rivalClearBtn">${esc(t('compareClear'))}</button>
      </div>
    </div>
    <div id="rivalComparison" aria-live="polite"></div>
    <div class="card">
      ${d.channels.length ? `<div class="rows">${d.channels.map(choiceRow).join('')}</div>`
                          : empty(d.hint || t('empty'))}
    </div>`;

  const displayBasket = () => {
    const current = getRivals();
    $('#rivalSelectedCount').textContent = t('compareSelected', { n: current.length });
    $('#rivalCompareBtn').disabled = current.length < 2;
    $('#rivalClearBtn').disabled = current.length === 0;
  };
  displayBasket();
  view.querySelectorAll('.rival-check').forEach((el) => el.addEventListener('change', () => {
    const id = el.dataset.channelId;
    const current = getRivals();
    if (el.checked && current.length >= 3) {
      el.checked = false;
      toast(t('compareMaxThree'), 'err');
      return;
    }
    saveRivals(el.checked ? [...current, id] : current.filter((x) => x !== id));
    $('#rivalComparison').innerHTML = '';
    displayBasket();
  }));
  $('#rivalClearBtn').addEventListener('click', () => {
    saveRivals([]);
    view.querySelectorAll('.rival-check').forEach((el) => { el.checked = false; });
    $('#rivalComparison').innerHTML = '';
    displayBasket();
  });
  $('#rivalCompareBtn').addEventListener('click', async () => {
    const ids = [...getRivals()];
    if (ids.length < 2) return;
    const button = $('#rivalCompareBtn');
    button.disabled = true;
    button.textContent = t('compareLoading');
    const target = $('#rivalComparison');
    try {
      // These GETs read previously collected Postgres data, never YouTube.
      const results = await Promise.allSettled(ids.map((id) =>
        api(`/api/channels/${encodeURIComponent(id)}${q({ period: state.period })}`)));
      if (target.isConnected && ids.join(',') === getRivals().join(',')) {
        target.innerHTML = rivalComparisonCard(ids, results);
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        const formatButton = target.querySelector('#rivalFormatsBtn');
        formatButton?.addEventListener('click', async () => {
          const examples = representativeVideos(ids, results);
          const report = target.querySelector('#rivalFormatResults');
          if (!report) return;
          formatButton.disabled = true;
          const evaluations = [];
          let processed = 0;
          const total = examples.filter((source) => source.videoId).length;
          try {
            for (const source of examples) {
              if (!source.videoId) {
                evaluations.push(null);
                continue;
              }
              if (!report.isConnected || ids.join(',') !== getRivals().join(',')) return;
              report.textContent = t('formatProgress', { processed, total });
              try {
                // Read-only local analysis: other channels across our WHOLE archive.
                // Sequential on purpose: cap expensive embedding/DB evaluations.
                const data = await api(`/api/videos/${encodeURIComponent(source.videoId)}/repeatability`);
                evaluations.push({ status: 'fulfilled', value: data });
              } catch (error) {
                evaluations.push({ status: 'rejected', reason: error });
              }
              processed++;
            }
            if (report.isConnected && ids.join(',') === getRivals().join(',')) {
              report.innerHTML = rivalFormatReport(examples, evaluations);
              report.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
          } finally {
            if (formatButton.isConnected) {
              formatButton.disabled = false;
              formatButton.textContent = t('formatReviewAgain');
            }
          }
        });
      }
    } finally {
      if (button.isConnected) {
        button.textContent = t('compareAction');
        displayBasket();
      }
    }
  });

  $('#applyChannels').addEventListener('click', () => {
    localStorage.setItem('nf.channels', JSON.stringify({
      min_multiplier: +$('#fcMult').value || 0,
      min_subscribers: $('#fcMinSubs').value ? +$('#fcMinSubs').value : '',
      max_subscribers: $('#fcMaxSubs').value ? +$('#fcMaxSubs').value : '',
      min_ypp_status: $('#fcYpp').value,
    }));
    render();
  });
}

export { viewChannels };
