/* YouTube Brain — ranking evidence, not a statistical confidence score.
   All values come from the existing niche ranking response. */
function count(value) {
  return Number.isSafeInteger(value) && value >= 0 ? value : null;
}

function evidence(entry = {}) {
  const coverage = entry.coverage;
  const weightPct = typeof coverage === 'number' && Number.isFinite(coverage)
    && coverage >= 0 && coverage <= 1 ? Math.round(coverage * 100) : null;
  const breakdown = Array.isArray(entry.breakdown) ? entry.breakdown : null;
  const available = breakdown
    ? breakdown.filter((part) => part && typeof part.value === 'number'
      && Number.isFinite(part.value) && typeof part.weight === 'number'
      && part.weight >= 0).length
    : null;
  return {
    totalVideos: count(entry.videos),
    distinctChannels: count(entry.channels),
    recentVideos: count(entry.recentVideos),
    knownWeightPct: weightPct,
    knownComponents: available,
    allComponents: breakdown ? breakdown.length : null,
    hasScore: typeof entry.score === 'number' && Number.isFinite(entry.score),
    missingReason: entry.reason === 'insufficient-data' || entry.reason === 'few-signals'
      ? entry.reason : null,
  };
}

export { evidence };
