import { getDb, connectDb } from './src/db/index.js';
import { resolveRequestedIdForDispatch, getModelGroups } from './src/services/model-groups.js';
import { getRoutingStrategy } from './src/services/router.js';

connectDb('./data/freeapi.db');
const db = getDb();

// We can just query `orderChain` directly by duplicating the scoring logic slightly,
// or we can just patch `router.js` in memory.
// Better, let's just copy the scoring logic for a moment to see the inputs:
import { getOrderedFusionChain } from './src/services/router.js';
const fusion = getOrderedFusionChain(100);
console.log('fusion:', fusion.filter(f => f.modelId.includes('gpt-oss-120b')));
