/* Read-only, opt-in repeatability comparison from existing video embeddings.
 * Reuses the already implemented /api/videos/:id/repeatability endpoint.
 * At most one representative long-form video per compared channel (max 3).
 */
import { api, esc } from './ui.js';
import { representativeVideos, repeatabilityEvidence } from './rival-formats.js';

const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
const VERDICT = {
  repeatable: 'formatRepeatable',
  mixed: 'formatMixed',
  one_off: 'formatOneOff',
  unknown: 'formatUnknown',
};
function formatCard(source, settled, t) {
  const video = source.videoId;
  if (!video || !VIDEO_ID.test(video)) {
    return `<div class="card">
      <strong>${esc(source.channelTitle)}</strong>
      <p class="section-sub">${esc(t('formatNoSource'))}</p>
    </div>`;
  }
  const safeUrl = 'https://www.youtube.com/watch?v=' + encodeURIComponent(video);
  if (settled?.status !== 'fulfilled') {
    return `<div class="card"><strong>${esc(source.channelTitle)}</strong>
      <p class="section-sub">${esc(t('formatRequestFailed'))}</p></div>`;
  }
  const r = repeatabilityEvidence(settled.value);
  const reason = r.reason === 'no-embedding' ? t('formatNoVectors') :
    r.verdict === 'unknown' ? t('formatInsufficient') : '';
  const line = t('formatEvidenceLine', {
    videos: r.similarVideos ?? '—',
    channels: r.independentChannels ?? '—',
    hit: r.hitChannels ?? '—',
  });
  const links = r.examples.map(x => {
    if (!VIDEO_ID.test(x.videoId)) return '';
    return `<li><a target="_blank" rel="noopener noreferrer"
      href="https://www.youtube.com/watch?v=${encodeURIComponent(x.videoId)}">
      ${esc(x.title)}</a> · ${esc(x.channelTitle)}</li>`;
  }).join('');
  return `<article class="card">
    <strong>${esc(source.channelTitle)}</strong>
    <p><a href="${safeUrl}" target="_blank" rel="noopener noreferrer">
      ${esc(source.title || video)}</a></p>
    <p><strong>${esc(t(VERDICT[r.verdict]))}</strong> · ${esc(line)}</p>
    ${reason ? `<p class="section-sub">${esc(reason)}</p>` : ''}
    ${links ? `<ul>${links}</ul>` : ''}
  </article>`;
}

function mountFormatReview(container, channelResults, t) {
  if (!container) return;
  const ids = channelResults.map(r => r.id);
  const settled = channelResults.map(r =>
    r.data ? { status: 'fulfilled', value: r.data } : { status: 'rejected' });
  const sources = representativeVideos(ids, settled);
  const eligible = sources.filter(s => s.videoId && VIDEO_ID.test(s.videoId));
  container.innerHTML = `<div class="card">
    <h3>${esc(t('formatReviewTitle'))}</h3>
    <p class="section-sub">${esc(t('formatReviewDescription'))}</p>
    <button class="btn" id="compareFormatsReview" type="button"
      ${eligible.length ? '' : 'disabled'}>${esc(t('formatReviewAction'))}</button>
    <div id="compareFormatsResult" aria-live="polite"></div>
  </div>`;
  const button = container.querySelector('#compareFormatsReview');
  const output = container.querySelector('#compareFormatsResult');
  button.addEventListener('click', async () => {
    button.disabled = true;
    const responses = [];
    for (const source of sources) {
      if (!source.videoId || !VIDEO_ID.test(source.videoId)) {
        responses.push({ status: 'rejected' });
        continue;
      }
      if (!container.isConnected) break;
      try {
        const value = await api('/api/videos/' + encodeURIComponent(source.videoId) + '/repeatability');
        responses.push({ status: 'fulfilled', value });
      } catch {
        responses.push({ status: 'rejected' });
      }
    }
    if (container.isConnected) {
      output.innerHTML = sources.map((source, i) => formatCard(source, responses[i], t)).join('')
        + `<p class="section-sub">${esc(t('formatCaveat'))}</p>`;
      button.disabled = false;
    }
  });
}
export { mountFormatReview };
