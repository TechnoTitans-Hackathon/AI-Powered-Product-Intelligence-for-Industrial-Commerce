import { spawn } from 'child_process';
import { exec } from 'child_process';
import http from 'http';

const OLLAMA_URL = 'http://127.0.0.1:11434';
const FREELLMAPI_URL = 'http://127.0.0.1:3001/v1';
const REQUIRED_MODEL = 'qwen3.5:9b-q4_K_M';
let ollamaProcess = null;

async function checkFreeLLMAPIRunning() {
  return new Promise((resolve) => {
    http.get(`${FREELLMAPI_URL}/models`, (res) => {
      resolve(res.statusCode === 200 || res.statusCode === 401);
    }).on('error', () => resolve(false));
  });
}

async function checkOllamaRunning() {
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
    }).on('error', () => {
      resolve({ running: false, hasModel: false });
    });
  });
}

async function startOllama() {
  console.log('Starting local Ollama instance with CUDA v12...');
  
  // Enforce CUDA v12 as required by architecture
  const env = { ...process.env, OLLAMA_LLM_LIBRARY: 'cuda_v12' };
  
  ollamaProcess = spawn('ollama', ['serve'], {
    env,
    stdio: 'ignore', // Ignore output to keep console clean, or we can pipe it
    detached: true,
    windowsHide: true
  });
  
  // Wait for it to be ready
  let ready = false;
  let attempts = 0;
  while (!ready && attempts < 30) {
    await new Promise(r => setTimeout(r, 1000));
    const status = await checkOllamaRunning();
    if (status.running) {
      ready = true;
      if (!status.hasModel) {
        console.error(`ERROR: Ollama started but required model ${REQUIRED_MODEL} is missing.`);
        process.exit(1);
      }
    }
    attempts++;
  }
  
  if (!ready) {
    console.error('ERROR: Timed out waiting for Ollama to start.');
    process.exit(1);
  }
  
  console.log('Ollama is ready.');
}

async function startDevServers() {
  console.log('Starting frontend and backend...');
  const devProcess = spawn('npx', ['concurrently', '"npm:dev:frontend"', '"npm:dev:backend"'], {
    stdio: 'inherit',
    shell: true
  });
  
  devProcess.on('close', (code) => {
    cleanup();
    process.exit(code);
  });
}

function cleanup() {
  if (ollamaProcess) {
    console.log('Shutting down Ollama instance started by dev script...');
    try {
      process.kill(-ollamaProcess.pid); // Kill process group
    } catch (e) {
      try {
        ollamaProcess.kill();
      } catch (err) {}
    }
  }
}

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);
process.on('exit', cleanup);

async function main() {
  console.log('Verifying FreeLLMAPI runtime...');
  const freellmapiRunning = await checkFreeLLMAPIRunning();
  
  if (!freellmapiRunning) {
    console.error('ERROR: FreeLLMAPI is not running on port 3001. Please start it using npm run dev in the freellmapi directory.');
    process.exit(1);
  } else {
    console.log('FreeLLMAPI is running.');
  }

  console.log('Verifying Ollama runtime...');
  const status = await checkOllamaRunning();
  
  if (status.running) {
    console.log('Ollama is already running. Reusing existing instance.');
    if (!status.hasModel) {
      console.error(`ERROR: Existing Ollama does not have required model ${REQUIRED_MODEL}.`);
      process.exit(1);
    }
  } else {
    await startOllama();
  }
  
  startDevServers();
}

main().catch(console.error);
