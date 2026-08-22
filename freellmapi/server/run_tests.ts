import { getDb, connectDb } from './src/db/index.js';
import './src/providers/index.js';
import { routeRequest } from './src/services/router.js';
import { setCooldown } from './src/services/ratelimit.js';
import { initEncryptionKey, encrypt } from './src/lib/crypto.js';

const db = connectDb();
initEncryptionKey(db);

function clear() {
  db.prepare('DELETE FROM rate_limit_cooldowns').run();
  db.prepare("DELETE FROM api_keys WHERE platform IN ('ovh', 'groq')").run();
}

import { encrypt } from './src/lib/crypto.js';

function insertKey(platform: string) {
  const enc = encrypt('fake-key');
  const row = db.prepare("INSERT INTO api_keys (platform, encrypted_key, iv, auth_tag, enabled, status, model_scope_json) VALUES (?, ?, ?, ?, 1, 'healthy', '[]') RETURNING id").get(platform, enc.encrypted, enc.iv, enc.authTag) as { id: number };
  return row.id;
}

function runTests() {
  console.log('--- TEST 1: OVH (cooldown) vs Groq (healthy) ---');
  clear();
  const ovhId = insertKey('ovh');
  const groqId = insertKey('groq');
  
  // Set OVH gpt-oss-120b on cooldown
  setCooldown('ovh', 'gpt-oss-120b', ovhId, 3600 * 1000, 429);
  
  try {
    const route = routeRequest(1000, undefined, undefined, false, false, undefined, [{
      model_db_id: 1, priority: 1, enabled: 1, platform: 'ovh', model_id: 'gpt-oss-120b', display_name: 'OVH', intelligence_rank: 5, size_label: '120B', supports_vision: 0, supports_tools: 0, context_window: 131000
    }, {
      model_db_id: 2, priority: 2, enabled: 1, platform: 'groq', model_id: 'gpt-oss-120b', display_name: 'Groq', intelligence_rank: 5, size_label: '120B', supports_vision: 0, supports_tools: 0, context_window: 131000
    }] as any[]);
    console.log('Selected Provider:', route.platform);
  } catch (e: any) {
    console.log('Error:', e.message);
    if (e.diagnostics) console.log('Diagnostics:', e.diagnostics);
  }

  console.log('\n--- TEST 2: OVH (healthy) vs Groq (healthy) ---');
  clear();
  insertKey('ovh');
  insertKey('groq');
  try {
    const route = routeRequest(1000, undefined, undefined, false, false, undefined, [{
      model_db_id: 1, priority: 1, enabled: 1, platform: 'ovh', model_id: 'gpt-oss-120b', display_name: 'OVH', intelligence_rank: 5, size_label: '120B', supports_vision: 0, supports_tools: 0, context_window: 131000
    }, {
      model_db_id: 2, priority: 2, enabled: 1, platform: 'groq', model_id: 'gpt-oss-120b', display_name: 'Groq', intelligence_rank: 5, size_label: '120B', supports_vision: 0, supports_tools: 0, context_window: 131000
    }] as any[]);
    console.log('Selected Provider:', route.platform);
  } catch (e: any) {
    console.log('Error:', e.message);
    if (e.diagnostics) console.log('Diagnostics:', e.diagnostics);
  }

  console.log('\n--- TEST 3: All providers blocked ---');
  clear();
  const ovh2Id = insertKey('ovh');
  const groq2Id = insertKey('groq');
  setCooldown('ovh', 'gpt-oss-120b', ovh2Id, 3600 * 1000, 429);
  setCooldown('groq', 'gpt-oss-120b', groq2Id, 3600 * 1000, 429);
  
  try {
    const route = routeRequest(1000, undefined, undefined, false, false, undefined, [{
      model_db_id: 1, priority: 1, enabled: 1, platform: 'ovh', model_id: 'gpt-oss-120b', display_name: 'OVH', intelligence_rank: 5, size_label: '120B', supports_vision: 0, supports_tools: 0, context_window: 131000
    }, {
      model_db_id: 2, priority: 2, enabled: 1, platform: 'groq', model_id: 'gpt-oss-120b', display_name: 'Groq', intelligence_rank: 5, size_label: '120B', supports_vision: 0, supports_tools: 0, context_window: 131000
    }] as any[]);
    console.log('Selected Provider:', route.platform);
  } catch (e: any) {
    console.log('Error:', e.message);
  }

  clear();
}

runTests();
