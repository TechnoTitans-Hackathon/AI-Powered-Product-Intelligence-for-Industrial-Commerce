import { getDb, connectDb } from './src/db/index.js';
connectDb('./data/freeapi.db');
const db = getDb();
console.log(db.prepare('SELECT id, model_id, platform, enabled FROM models WHERE id IN (164, 166, 203, 165, 168, 201)').all());
