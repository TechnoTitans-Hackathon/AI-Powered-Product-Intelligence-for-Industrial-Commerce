import { getDb, connectDb } from './src/db/index.js';
import { resolveRequestedIdForDispatch, getModelGroups } from './src/services/model-groups.js';
import { resolveModelGroupCandidates } from './src/services/router.js';

connectDb('./data/freeapi.db');
const groups = getModelGroups();
const resolved = resolveRequestedIdForDispatch('gpt-oss-120b', groups);

if (resolved) {
  // We need to bypass the sampled score to see the deterministic score.
  // Actually, let's just log the raw scoreChainEntry.
  // We can just patch orderChain in our head or run it multiple times.
  const chain = resolveModelGroupCandidates(resolved.memberDbIds, resolved.demotedDbIds);
  console.log(JSON.stringify(chain.map(f => ({ platform: f.platform, priority: f.priority, model_id: f.model_id })), null, 2));
}
