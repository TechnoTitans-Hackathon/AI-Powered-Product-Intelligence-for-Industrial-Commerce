import { spawn, execSync } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const OLLAMA_URL = 'http://127.0.0.1:11434';
const REQUIRED_MODEL = 'qwen3.5:9b-q4_K_M';
const FREELLMAPI_URL = 'http://127.0.0.1:3001/v1';
const BACKEND_URL = 'http://127.0.0.1:8000';

let spawnedProcesses = [];

// Clean up spawned processes on exit
function cleanup() {
  for (const proc of spawnedProcesses) {
    if (proc && proc.pid) {
      try {
        if (process.platform === 'win32') {
          execSync(`taskkill /F /T /PID ${proc.pid}`, { stdio: 'ignore' });
        } else {
          process.kill(-proc.pid);
        }
      } catch (err) {
        // Ignore errors during cleanup
      }
    }
  }
  spawnedProcesses = [];
}

process.on('SIGINT', () => {
  cleanup();
  process.exit(0);
});
process.on('SIGTERM', () => {
  cleanup();
  process.exit(0);
});
process.on('exit', cleanup);

async function checkUrl(url, method = 'GET') {
  return new Promise((resolve) => {
    const req = http.request(url, { method }, (res) => {
      resolve(res.statusCode);
    });
    req.on('error', () => resolve(0));
    req.end();
  });
}

async function checkOllama() {
  return new Promise((resolve) => {
    http.get(`${OLLAMA_URL}/api/tags`, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          const hasModel = parsed.models && parsed.models.some(m => m.name === REQUIRED_MODEL);
          resolve({ running: true, hasModel });
        } catch (e) {
          resolve({ running: true, hasModel: false });
        }
      });
    }).on('error', () => resolve({ running: false, hasModel: false }));
  });
}

async function startOllama() {
  const env = { ...process.env, OLLAMA_LLM_LIBRARY: 'cuda_v12' };
  const proc = spawn('ollama', ['serve'], {
    env,
    stdio: 'ignore',
    detached: process.platform !== 'win32',
    windowsHide: true,
    shell: true
  });
  spawnedProcesses.push(proc);

  let ready = false;
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const status = await checkOllama();
    if (status.running) {
      ready = true;
      if (!status.hasModel) {
        return false;
      }
      break;
    }
  }
  return ready;
}

async function startFreeLLMAPI() {
  const targetDir = path.join(__dirname, 'freellmapi');
  if (!fs.existsSync(path.join(targetDir, 'package.json'))) {
    console.error(`[FAIL] FreeLLMAPI package.json not found in ${targetDir}`);
    return false;
  }

  const proc = spawn('npm run dev', {
    cwd: targetDir,
    stdio: 'ignore',
    shell: true
  });
  spawnedProcesses.push(proc);

  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const status = await checkUrl(`${FREELLMAPI_URL}/models`);
    if (status > 0) return true;
  }
  return false;
}

async function startBackend() {
  const targetDir = path.join(__dirname, 'Frontend+Backend + Ai Engine');

  const command = process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python';
  const proc = spawn(`${command} -m uvicorn backend.main:app --port 8000`, {
    cwd: targetDir,
    stdio: 'ignore',
    shell: true
  });
  spawnedProcesses.push(proc);

  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const status = await checkUrl(`${BACKEND_URL}/docs`);
    if (status === 200) return true;
  }
  return false;
}

async function startFrontend() {
  return new Promise((resolve) => {
    const targetDir = path.join(__dirname, 'Frontend+Backend + Ai Engine', 'frontend');
    const proc = spawn('npm run dev:frontend', {
      cwd: targetDir,
      shell: true
    });
    spawnedProcesses.push(proc);

    let resolved = false;
    proc.stdout.on('data', (data) => {
      const output = data.toString();
      const match = output.match(/http:\/\/(localhost|127\.0\.0\.1):(\d+)/);
      if (match && !resolved) {
        resolved = true;
        resolve(match[0]);
      }
    });

    proc.on('error', () => {
      if (!resolved) {
        resolved = true;
        resolve(null);
      }
    });

    // Timeout fallback
    setTimeout(() => {
      if (!resolved) {
        resolved = true;
        resolve(null);
      }
    }, 20000);
  });
}

async function main() {
  // 1. OLLAMA
  console.log('\n[1/5] Checking Ollama...');
  let ollamaStatus = await checkOllama();

  if (ollamaStatus.running) {
    console.log('[OK] Ollama');
  } else {
    const started = await startOllama();
    if (!started) {
      console.log('[FAIL] Ollama could not be started.');
      process.exit(1);
    }
    console.log('[OK] Ollama');
    ollamaStatus = await checkOllama(); // refresh status
  }

  // 2. QWEN MODEL
  console.log('\n[2/5] Checking Qwen3.5...');
  if (ollamaStatus.hasModel) {
    console.log(`[OK] ${REQUIRED_MODEL}`);
  } else {
    console.log(`[FAIL] ${REQUIRED_MODEL} is not installed.`);
    console.log('Run:');
    console.log(`ollama pull ${REQUIRED_MODEL}`);
    process.exit(1);
  }

  // 3. FREELLMAPI
  console.log('\n[3/5] Checking FreeLLMAPI...');
  let freellmapiStatus = await checkUrl(`${FREELLMAPI_URL}/models`);
  if (freellmapiStatus > 0) {
    console.log('[OK] FreeLLMAPI');
  } else {
    const started = await startFreeLLMAPI();
    if (!started) {
      console.log('[FAIL] FreeLLMAPI could not be started/reached.');
      process.exit(1);
    }
    console.log('[OK] FreeLLMAPI');
  }

  // 4. BACKEND
  console.log('\n[4/5] Starting Backend...');
  let backendStatus = await checkUrl(`${BACKEND_URL}/docs`);
  if (backendStatus === 200) {
    console.log('[OK] Backend');
  } else {
    const started = await startBackend();
    if (!started) {
      console.log('[FAIL] UniHack backend failed to start.');
      process.exit(1);
    }
    console.log('[OK] Backend');
  }

  // 5. FRONTEND
  console.log('\n[5/5] Starting Frontend...');
  let frontendUrl = 'http://localhost:5173';
  let frontendStatus = await checkUrl(frontendUrl);
  if (frontendStatus === 200) {
    console.log('[OK] Frontend');
  } else {
    const actualUrl = await startFrontend();
    if (!actualUrl) {
      console.log('[FAIL] Frontend could not be started.');
      process.exit(1);
    }
    frontendUrl = actualUrl;
    console.log('[OK] Frontend');
  }

  console.log('\n==========================================');
  console.log('UNIHACK IS READY');
  console.log('==========================================');
  console.log(`Frontend: ${frontendUrl}`);
  console.log(`Backend:  ${BACKEND_URL}`);
  console.log('==========================================\n');

  // Keep event loop alive
  setInterval(() => {}, 1000 * 60 * 60);
}

main().catch(console.error);
