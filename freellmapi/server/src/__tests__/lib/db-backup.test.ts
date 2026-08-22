import fs from 'fs';
import os from 'os';
import path from 'path';
import Database from 'better-sqlite3';
import { afterEach, describe, expect, it } from 'vitest';
import { backupDbNow, restoreDbBackupIfNeeded } from '../../lib/db-backup.js';
import { aclEntries } from '../helpers/acl.js';

const ORIGINAL_BACKUP_PATH = process.env.FREEAPI_DB_BACKUP_PATH;
const ORIGINAL_BACKUP_TARGET = process.env.FREEAPI_DB_BACKUP_TARGET;
const ORIGINAL_BACKUP_URL = process.env.FREEAPI_DB_BACKUP_URL;
const ORIGINAL_BACKUP_KEY = process.env.FREEAPI_DB_BACKUP_KEY;
const ORIGINAL_ENCRYPTION_KEY = process.env.ENCRYPTION_KEY;

function restoreEnv() {
  if (ORIGINAL_BACKUP_PATH === undefined) delete process.env.FREEAPI_DB_BACKUP_PATH;
  else process.env.FREEAPI_DB_BACKUP_PATH = ORIGINAL_BACKUP_PATH;
  if (ORIGINAL_BACKUP_TARGET === undefined) delete process.env.FREEAPI_DB_BACKUP_TARGET;
  else process.env.FREEAPI_DB_BACKUP_TARGET = ORIGINAL_BACKUP_TARGET;
  if (ORIGINAL_BACKUP_URL === undefined) delete process.env.FREEAPI_DB_BACKUP_URL;
  else process.env.FREEAPI_DB_BACKUP_URL = ORIGINAL_BACKUP_URL;
  if (ORIGINAL_BACKUP_KEY === undefined) delete process.env.FREEAPI_DB_BACKUP_KEY;
  else process.env.FREEAPI_DB_BACKUP_KEY = ORIGINAL_BACKUP_KEY;
  if (ORIGINAL_ENCRYPTION_KEY === undefined) delete process.env.ENCRYPTION_KEY;
  else process.env.ENCRYPTION_KEY = ORIGINAL_ENCRYPTION_KEY;
}

describe('encrypted SQLite backup', () => {
  afterEach(() => restoreEnv());

  it('backs up and restores a SQLite file from a configured path', async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'freeapi-db-backup-'));
    const dbPath = path.join(dir, 'freeapi.db');
    const backupPath = path.join(dir, 'backup.bin');
    process.env.ENCRYPTION_KEY = 'a'.repeat(64);
    process.env.FREEAPI_DB_BACKUP_PATH = backupPath;

    const db = new Database(dbPath);
    db.exec('CREATE TABLE items (name TEXT NOT NULL); INSERT INTO items (name) VALUES (\'survived\')');
    const backup = await backupDbNow(db, dbPath);
    db.close();

    expect(backup.ok).toBe(true);
    expect(fs.existsSync(backupPath)).toBe(true);
    expect(fs.readFileSync(backupPath).includes(Buffer.from('survived'))).toBe(false);

    fs.rmSync(dbPath);
    const restore = await restoreDbBackupIfNeeded(dbPath);
    expect(restore.restored).toBe(true);

    const restored = new Database(dbPath);
    expect((restored.prepare('SELECT name FROM items').get() as { name: string }).name).toBe('survived');
    restored.close();
  });
});

describe('backup file permissions', () => {
  // The blob is AES-256-GCM encrypted and the restored file is a plain SQLite
  // database, but both live on a host that also holds the key — usually in a
  // .env in the same tree — so neither may be left world-readable.
  //
  // As elsewhere, each platform asserts what it can actually enforce: Node
  // synthesizes a 0o666 mode on Windows regardless of the ACL, so a POSIX-mode
  // assertion there would pass or fail for reasons unrelated to the guarantee.
  const isWindows = process.platform === 'win32';
  const itPosix = it.skipIf(isWindows);
  const itWindows = it.skipIf(!isWindows);

  afterEach(() => restoreEnv());

  async function backupInto(dir: string): Promise<string> {
    const dbPath = path.join(dir, 'freeapi.db');
    const backupPath = path.join(dir, 'backup.bin');
    process.env.ENCRYPTION_KEY = 'a'.repeat(64);
    process.env.FREEAPI_DB_BACKUP_PATH = backupPath;

    const db = new Database(dbPath);
    db.exec('CREATE TABLE items (name TEXT NOT NULL)');
    await backupDbNow(db, dbPath);
    db.close();
    return backupPath;
  }

  itPosix('writes the backup blob owner-only', async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'freeapi-backup-perms-'));
    const backupPath = await backupInto(dir);

    expect(fs.statSync(backupPath).mode & 0o077).toBe(0);
  });

  itPosix('tightens a backup target that already existed', async () => {
    // writeFileSync's mode argument only applies when the file is created, so
    // every backup after the first overwrites a file that keeps whatever mode
    // it already had. Without the explicit restrict call this is the case that
    // stays group-readable forever.
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'freeapi-backup-perms-'));
    const backupPath = path.join(dir, 'backup.bin');
    fs.writeFileSync(backupPath, 'stale');
    // chmod rather than a creation mode: the mode argument is filtered through
    // the runner's umask, so a strict umask would leave this pre-condition
    // asserting the very thing it means to rule out.
    fs.chmodSync(backupPath, 0o644);
    expect(fs.statSync(backupPath).mode & 0o077).not.toBe(0);

    await backupInto(dir);

    expect(fs.statSync(backupPath).mode & 0o077).toBe(0);
  });

  itPosix('writes the restored database owner-only', async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'freeapi-backup-perms-'));
    const dbPath = path.join(dir, 'freeapi.db');
    await backupInto(dir);
    fs.rmSync(dbPath);

    // The restore lands before connectDb runs, and sometimes in a different
    // process entirely; the decrypted database must not be readable in between.
    expect((await restoreDbBackupIfNeeded(dbPath)).restored).toBe(true);
    expect(fs.statSync(dbPath).mode & 0o077).toBe(0);
  });

  itWindows('replaces the inherited ACL on the backup blob', async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'freeapi-backup-perms-'));
    const backupPath = await backupInto(dir);

    const entries = aclEntries(backupPath);
    expect(entries.filter(e => e.includes('(I)'))).toEqual([]);
    expect(entries).toHaveLength(3);
  });
});
