import { connectDb, regenerateUnifiedKey } from './src/db/index.js';
connectDb('d:/Hackathon/freellmapi/server/data/freeapi.db');
const key = regenerateUnifiedKey();
console.log('NEW_UNIFIED_KEY=' + key);
