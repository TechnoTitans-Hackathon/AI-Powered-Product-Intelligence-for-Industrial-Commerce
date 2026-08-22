const db = require('better-sqlite3')('data/freeapi.db');
db.prepare("UPDATE api_keys SET status = 'healthy', enabled = 1 WHERE platform = 'pollinations'").run();
console.log('Updated pollinations key to healthy');
