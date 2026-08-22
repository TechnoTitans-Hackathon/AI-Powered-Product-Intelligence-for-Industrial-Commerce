import { getDb, connectDb } from './src/db/index.js';
connectDb('./data/freeapi.db');
const db = getDb();
console.log(db.prepare("SELECT * FROM fallback_config").all());
