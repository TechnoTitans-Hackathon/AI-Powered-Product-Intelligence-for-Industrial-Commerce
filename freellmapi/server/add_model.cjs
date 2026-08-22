const db = require('better-sqlite3')('data/freeapi.db');
db.prepare("INSERT INTO models (platform, model_id, display_name, intelligence_rank, size_label, supports_vision, supports_tools, enabled, source) VALUES ('pollinations', 'gpt-oss-120b', 'Pollinations GPT', 5, '120B', 0, 0, 1, 'user')").run();
console.log('Added pollinations');
