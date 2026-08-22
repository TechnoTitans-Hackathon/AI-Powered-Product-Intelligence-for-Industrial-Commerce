import { connectDb, getDb } from './src/db/index.js';
connectDb();
console.log(getDb().prepare("SELECT key, value FROM settings WHERE key LIKE '%unify%'").all());
