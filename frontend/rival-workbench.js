/* Research-only YouTube Brain competitor comparison.
 * Uses already archived channel analytics; no YouTube API request, scoring or LLM.
 * A zero is valid; missing and inconsistent values remain null.
 */
const value = (v) => typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : null;
const integer = (v) => Number.isSafeInteger(v) && v >= 0 ? v : null;

function rivalSnapshot(data = {}) {
  const p = data.profile || {};
  const c = data.cadence || {};
  const perf = data.performance || {};
  const g = data.growth?.['30d'] || {};
  const reported = integer(p.videoCount);
  const analysed = integer(perf.videosAnalysed);
  return {
    title: typeof p.title === 'string' ? p.title : '',
    subscribers: integer(p.subscribers),
    reportedVideos: reported,
    analysedVideos: analysed,
    archivePercent: reported != null && reported > 0
      && analysed != null && analysed <= reported
      ? Math.round(analysed / reported * 100) : null,
    uploadsInPeriod: integer(c.uploadsInPeriod),
    lifetimeUploadsWeekly: value(c.uploadsPerWeekLifetime),
    shortsCount: integer(c.shortsCount),
    longformCount: integer(c.longformCount),
    shortsShare: value(c.shortsSharePercent) <= 100 ? value(c.shortsSharePercent) : null,
    shortsMedianViews: value(perf.shortsMedianViews),
    longformMedianViews: value(perf.longformMedianViews),
    medianViews: value(perf.medianViewsPerVideo),
    viewsPerDay30d: value(g.views?.per_day),
    subscribersPerDay30d: value(g.subscribers?.per_day),
    bestOutlier: Array.isArray(data.topOutliers)
      ? value(data.topOutliers[0]?.outlierScore) : null,
    snapshots: integer(data.snapshots),
    vanished: !!data.gone,
  };
}

function parseRivalBasket(raw, max = 3) {
  let ids;
  try { ids = JSON.parse(raw || '[]'); } catch { return []; }
  if (!Array.isArray(ids)) return [];
  const unique = [];
  for (const id of ids) {
    if (typeof id === 'string' && /^UC[A-Za-z0-9_-]{10,40}$/.test(id)
      && !unique.includes(id)) unique.push(id);
    if (unique.length === max) break;
  }
  return unique;
}

export { rivalSnapshot, parseRivalBasket };
