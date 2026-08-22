const db = require('better-sqlite3')('./data/freeapi.db');
console.log(db.prepare("SELECT m.id, m.platform, m.model_id, fc.priority FROM models m LEFT JOIN fallback_config fc ON fc.model_db_id = m.id WHERE m.model_id = 'gpt-oss-120b' OR m.model_id = 'openai/gpt-oss-120b'").all());
