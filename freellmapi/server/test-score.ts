import { getDb, connectDb } from './src/db/index.js';
import { resolveRequestedIdForDispatch, getModelGroups } from './src/services/model-groups.js';
import { resolveModelGroupCandidates } from './src/services/router.js';
import { scoreChainEntry, BANDIT_PRESETS } from './src/services/scoring.js';

connectDb('./data/freeapi.db');
const db = getDb();

const groups = getModelGroups();
const resolved = resolveRequestedIdForDispatch('gpt-oss-120b', groups);

if (resolved) {
  const chain = resolveModelGroupCandidates(resolved.memberDbIds, resolved.demotedDbIds);
  const intelMin = Math.min(...chain.map(c => c.intelligence_rank));
  const intelMax = Math.max(...chain.map(c => c.intelligence_rank));
  const keyCounts = new Map<string, number>(); // mock
  for (const entry of chain) {
    keyCounts.set(entry.platform, 1);
  }

  const scored = chain.map(e => {
    return {
      platform: e.platform,
      priority: e.priority,
      score: scoreChainEntry(e, BANDIT_PRESETS.balanced, intelMin, intelMax, false, keyCounts)
    };
  });
  console.log(JSON.stringify(scored, null, 2));
}
