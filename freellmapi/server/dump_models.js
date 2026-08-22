import { connectDb, getDb } from './src/db/index.js';
connectDb();
console.log(getDb().prepare("SELECT id, platform, model_id, display_name FROM models WHERE model_id LIKE '%qwen%'").all());
