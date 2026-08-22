import { getDb, connectDb } from './src/db/index.js';
connectDb();
const db = getDb();
console.log(db.prepare('SELECT id, platform, status, enabled, base_url FROM api_keys WHERE id = 3').get());
