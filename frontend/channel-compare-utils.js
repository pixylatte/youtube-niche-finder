/* Shareable, quota-free comparison selection. Only YouTube channel IDs.
   No URL state is persisted in localStorage and no collected data is copied. */
// Canonical YouTube IDs are 24 chars; seeded local demo IDs can be 22.
const CHANNEL_ID = /^UC[A-Za-z0-9_-]{20,22}$/;
const MAX_CHANNELS = 3;

function normalizeChannelIds(raw) {
  const values = Array.isArray(raw) ? raw : String(raw || '').split(',');
  const ids = [];
  for (const v of values) {
    if (typeof v !== 'string') continue;
    let id;
    try { id = decodeURIComponent(v.trim()); }
    catch { continue; }
    if (!CHANNEL_ID.test(id) || ids.includes(id)) continue;
    ids.push(id);
    if (ids.length === MAX_CHANNELS) break;
  }
  return ids;
}

function channelCompareHref(raw) {
  const ids = normalizeChannelIds(raw);
  return ids.length >= 2
    ? `#/channel-compare/${ids.map(encodeURIComponent).join(',')}`
    : null;
}

export { MAX_CHANNELS, normalizeChannelIds, channelCompareHref };
