// One minimal GPT-OSS request through FreeLLMAPI
const fs = require('fs');
const path = require('path');

const backendEnv = fs.readFileSync(path.join('..', 'Frontend+Backend + Ai Engine', '.env'), 'utf8');
const match = backendEnv.match(/FREELLMAPI_API_KEY=(.+)/);
const apiKey = match[1].trim();

async function test() {
  const start = Date.now();
  const resp = await fetch('http://localhost:3001/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model: 'gpt-oss-120b',
      messages: [{ role: 'user', content: 'Return exactly JSON {"ok":true}' }],
      max_tokens: 20
    })
  });
  const latency = Date.now() - start;
  
  console.log("STATUS:", resp.status);
  
  // Print relevant headers
  for (const [k, v] of resp.headers.entries()) {
    if (k.startsWith('x-') || k.includes('retry')) {
      console.log(`  ${k}: ${v}`);
    }
  }
  
  const body = await resp.json();
  console.log("LATENCY:", latency, "ms");
  console.log("BODY:", JSON.stringify(body, null, 2));
}

test().catch(e => console.error("FETCH ERROR:", e.message));
