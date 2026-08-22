const crypto = require('crypto');
const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');

const ALGORITHM = 'aes-256-gcm';
const KEY_BYTES = 32;

const keyHex = fs.readFileSync(path.join(__dirname, 'data', '.encryption-key'), 'utf8').trim();
const key = Buffer.from(keyHex, 'hex');

function encrypt(text) {
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipheriv(ALGORITHM, key, iv);

  let encrypted = cipher.update(text, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  const authTag = cipher.getAuthTag().toString('hex');

  return {
    encrypted,
    iv: iv.toString('hex'),
    authTag,
  };
}

const db = new Database(path.join(__dirname, 'data', 'freeapi.db'));

const { encrypted, iv, authTag } = encrypt('dummy_ollama_key');

// Clear existing ollama keys just in case
db.prepare('DELETE FROM api_keys WHERE platform = ?').run('ollama');

// Insert new key
const stmt = db.prepare(`
  INSERT INTO api_keys (platform, label, encrypted_key, iv, auth_tag, status, enabled, base_url, created_at)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
`);

const info = stmt.run(
  'ollama',
  'ollama-local',
  encrypted,
  iv,
  authTag,
  'valid',
  1,
  'http://127.0.0.1:11434'
);

console.log('Inserted key for ollama:', info);
db.close();
