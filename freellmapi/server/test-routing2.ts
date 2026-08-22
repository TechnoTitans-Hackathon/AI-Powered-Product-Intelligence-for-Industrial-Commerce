import { getDb, connectDb } from './src/db/index.js';
import { getRoutingStrategy } from './src/services/router.js';
import { resolveRequestedIdForDispatch, getModelGroups } from './src/services/model-groups.js';
import { resolveModelGroupCandidates } from './src/services/router.js';

connectDb('./data/freeapi.db');
const db = getDb();
console.log('Strategy:', getRoutingStrategy());

const groups = getModelGroups();
const resolved = resolveRequestedIdForDispatch('gpt-oss-120b', groups);

if (resolved) {
  const chain = resolveModelGroupCandidates(resolved.memberDbIds, resolved.demotedDbIds);
  const filtered = chain.filter(e => {
    const keys = db.prepare(`SELECT * FROM api_keys WHERE platform = ? AND enabled = 1 AND status IN ('healthy', 'unknown')`).all(e.platform);
    return keys.length > 0;
  });
  console.log(JSON.stringify(filtered.map(f => ({ platform: f.platform, priority: f.priority, model_id: f.model_id })), null, 2));
}
