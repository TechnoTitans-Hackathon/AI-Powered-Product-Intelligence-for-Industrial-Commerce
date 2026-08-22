import { getDb, connectDb } from './src/db/index.js';
import { resolveRequestedIdForDispatch, getModelGroups } from './src/services/model-groups.js';

connectDb('./data/freeapi.db');
const groups = getModelGroups();
const resolved = resolveRequestedIdForDispatch('gpt-oss-120b', groups);

if (resolved) {
  const db = getDb();
  console.log('memberDbIds:', resolved.memberDbIds);
  const models = db.prepare(`SELECT id, platform, model_id FROM models WHERE id IN (${resolved.memberDbIds.join(',')})`).all();
  console.log('models:', models);
  
  const keys = db.prepare(`SELECT id, platform, status, enabled, model_scope_json FROM api_keys`).all();
  console.log('all keys:', keys);
}
