import { getDb, connectDb } from './src/db/index.js';
connectDb();
const db = getDb();
db.prepare("UPDATE api_keys SET status = 'healthy', base_url = 'http://127.0.0.1:8080/v1' WHERE platform = 'custom'").run();
console.log('updated custom key');
