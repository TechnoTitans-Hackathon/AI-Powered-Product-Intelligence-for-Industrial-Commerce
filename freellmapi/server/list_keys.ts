import { connectDb } from './src/db/index.js';
const db = connectDb('d:/Hackathon/freellmapi/server/data/freeapi.db');
const keys = db.prepare('SELECT id, platform, label, status FROM api_keys').all();
console.log(JSON.stringify(keys, null, 2));
