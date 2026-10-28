/* YouTube Brain: representative long-video formats from an existing rival comparison.
 * Reuses the read-only /api/videos/:id/repeatability algorithm.
 * The source's topOutliers are long-form only; one selected video per channel.
 * No YouTube search, no LLM calls, no invented evidence.
 */
const natural = (n) => Number.isSafeInteger(n) && n >= 0 ? n : null;
const finite = (n) => typeof n === 'number' && Number.isFinite(n) && n >= 0 ? n : null;
const validId = (id) => typeof id === 'string' && /^[a-zA-Z0-9_-]{1,64}$/.test(id);

function representativeVideos(ids = [], results = []) {
  return ids.slice(0, 3).map((channelId, index) => {
    const settled = results[index];
    const data = settled?.status === 'fulfilled' && settled.value?.found !== false
      ? settled.value : null;
    const best = Array.isArray(data?.topOutliers)
      ? data.topOutliers.find((video) => validId(video?.videoId)) : null;
    return {
      channelId,
      channelTitle: data?.profile?.title || channelId,
      videoId: best?.videoId ?? null,
      title: best?.title || null,
      outlierScore: finite(best?.outlierScore),
    };
  });
}

function repeatabilityEvidence(data = {}) {
  const verdict = ['repeatable', 'mixed', 'one_off', 'unknown'].includes(data.verdict)
    ? data.verdict : 'unknown';
  const reason = data.reason === 'no-embedding' ? 'no-embedding'
    : data.reason === 'few-similar-videos' ? 'few-similar-videos' : null;
  const examples = Array.isArray(data.examples) ? data.examples
    .filter((v) => validId(v?.videoId) && validId(v?.channelId))
    .slice(0, 3).map((v) => ({
      videoId: v.videoId,
      title: typeof v.title === 'string' ? v.title : v.videoId,
      channelTitle: typeof v.channelTitle === 'string' ? v.channelTitle : '',
      outlierScore: finite(v.outlierScore),
    })) : [];
  return {
    verdict, reason,
    similarVideos: natural(data.similarVideos),
    independentChannels: natural(data.channels),
    hitChannels: natural(data.channelsHit),
    hitScore: finite(data.hitScore),
    medianChannelBest: finite(data.medianChannelBest),
    examples,
  };
}

export { representativeVideos, repeatabilityEvidence };
