const db = require('better-sqlite3')('data/freeapi.db');
const rows = db.prepare("SELECT platform, model_id FROM models WHERE model_id LIKE '%gpt-oss%'").all();
console.log(rows);
