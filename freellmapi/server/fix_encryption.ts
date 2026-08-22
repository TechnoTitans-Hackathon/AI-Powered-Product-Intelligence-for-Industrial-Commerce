import { getDb, connectDb } from './src/db/index.js';
import { encrypt } from './src/lib/crypto.js';
import { initEncryptionKey } from './src/lib/crypto.js';

async function fix() {
    connectDb();
    const db = getDb();
    await initEncryptionKey(db);
    const enc = encrypt('mock-key');
    db.prepare("UPDATE api_keys SET encrypted_key = ?, iv = ?, auth_tag = ? WHERE id = 3").run(enc.encrypted, enc.iv, enc.authTag);
    console.log('Fixed encryption for custom key');
}
fix();
