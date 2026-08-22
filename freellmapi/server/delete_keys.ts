import { connectDb } from './src/db/index.js';
const db = connectDb('d:/Hackathon/freellmapi/server/data/freeapi.db');
db.prepare('DELETE FROM api_keys WHERE id = 2').run();
db.prepare('DELETE FROM api_keys WHERE id = 7').run();
console.log('Deleted corrupted keys.');
