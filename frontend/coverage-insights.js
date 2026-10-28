/* YouTube Brain — exact archive coverage facts only.
 * No scoring, extrapolation, network requests, storage or quota usage.
 * /api/overview.coverage counts the WHOLE archive, not the selected niche.
 */
function count(value) {
  return Number.isSafeInteger(value) && value >= 0 ? value : null;
}

function percent(part, total) {
  if (part == null || total == null || total <= 0 || part > total) return null;
  return Math.round((part / total) * 100);
}

function archiveCoverage(coverage = {}, stats = {}) {
  const total = count(coverage.videosTotal);
  const period = count(coverage.videosPublishedInPeriod);
  const history = count(coverage.videosWithHistory);
  const categories = count(coverage.videosWithCategory);
  const missingVectors = count(stats.videos_without_embedding);
  const vectors = total != null && missingVectors != null && missingVectors <= total
    ? total - missingVectors : null;

  return {
    total,
    period,
    history,
    categories,
    vectors,
    periodPct: percent(period, total),
    historyPct: percent(history, total),
    categoriesPct: percent(categories, total),
    vectorsPct: percent(vectors, total),
    // A threshold of 5 only marks sparse samples; passing it is NOT validation.
    periodSparse: period != null && period < 5,
    historyMissing: total > 0 && history === 0,
    vectorsMissing: total > 0 && vectors != null && vectors < total,
  };
}

export { archiveCoverage };
