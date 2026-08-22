import { getDb, connectDb } from './src/db/index.js';
connectDb();
const db = getDb();
console.log(db.prepare("SELECT * FROM models WHERE model_id = 'gpt-oss-120b'").all());
