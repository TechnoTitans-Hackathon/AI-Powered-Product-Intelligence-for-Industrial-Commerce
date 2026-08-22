import { getDb, connectDb } from './src/db/index.js';
connectDb();
import { resolveRoutingChain } from './src/services/router.js';
console.log(resolveRoutingChain('gpt-oss-120b').chain.map(x => x.platform).join(', '));
