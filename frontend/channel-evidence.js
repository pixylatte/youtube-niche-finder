/* YouTube Brain: evidence that already exists in channel endpoints.
 * No network calls, no opaque "confidence score", no new YouTube API quota.
 * Velocity is a limited sample, never a percentage of all channel uploads.
 */
const nonNegativeInt = (n) => Number.isSafeInteger(n) && n >= 0 ? n : null;
const nonNegativeMetric = (n) => typeof n === 'number' &&
  Number.isFinite(n) && n >= 0 ? n : null;

function channelEvidence(analytics = {}, velocity = {}, history = {}, similar = {}) {
  const reported = nonNegativeInt(analytics.profile?.videoCount);
  const collected = nonNegativeInt(analytics.performance?.videosAnalysed);
  const snapshotCount = nonNegativeInt(history.count);
  const sampled = Array.isArray(velocity.videos) ? velocity.videos : null;
  const sampledCount = sampled ? sampled.length : null;
  const vphAvailable = sampled
    ? sampled.filter((item) => nonNegativeMetric(item?.vph24h) !== null).length
    : null;
  const embedded = nonNegativeInt(similar.videosEmbedded);
  const growth = analytics.growth && typeof analytics.growth === 'object' ?
    analytics.growth : {};
  const observedGrowthWindows = ['24h', '7d', '30d', '90d'].filter((w) => {
    const row = growth[w];
    return !!row && (!!row.views || !!row.subscribers);
  });

  return {
    reported, collected, snapshotCount, sampledCount, vphAvailable, embedded,
    observedGrowthWindows,
    // Only show a percentage if the two counts can form a valid denominator.
    // 'collected' reflects the local archive; reported is the channel's API count.
    archivePercent: reported != null && reported > 0 &&
      collected != null && collected <= reported
      ? Math.round(collected / reported * 100) : null,
    archiveIncomplete: reported != null && collected != null && collected < reported,
    historyInsufficient: snapshotCount != null && snapshotCount < 2,
    velocityInsufficient: sampledCount != null && sampledCount > 0 && vphAvailable === 0,
    embeddingMissing: embedded === 0,
  };
}

export { channelEvidence };
