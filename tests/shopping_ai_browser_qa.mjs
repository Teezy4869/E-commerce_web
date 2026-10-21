// Phase 7 browser journey. Run only against a temporary COGU_CATALOG_DB.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

if (process.env.COGU_BROWSER_QA_TEMP_DB !== '1') throw new Error('Use a temporary COGU_CATALOG_DB and set COGU_BROWSER_QA_TEMP_DB=1.');
const base = process.env.COGU_BASE_URL || 'http://127.0.0.1:8765/';
const port = 19227;
const chrome = spawn(process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-allow-origins=*',
    `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'cogu-ai-browser-'))}`, 'about:blank'],
  { windowsHide: true, stdio: 'ignore' });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket; let serial = 0; const pending = new Map();
async function target() {
  for (let i = 0; i < 60; i++) {
    try { const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); const page = pages.find(item => item.type === 'page'); if (page) return page; }
    catch { /* Starting. */ }
    await sleep(150);
  }
  throw new Error('Chrome DevTools did not start.');
}
function command(method, params = {}) {
  const id = ++serial;
  return new Promise((resolve, reject) => { pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params })); });
}
async function evaluate(expression) {
  const response = await command('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
  if (response.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text);
  return response.result.value;
}
async function until(expression, timeout = 10000) {
  const start = Date.now();
  while (Date.now() - start < timeout) { try { if (await evaluate(expression)) return; } catch { /* Navigation. */ } await sleep(120); }
  throw new Error(`Timed out: ${expression}`);
}
async function screenshot(label) {
  const image = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  const path = join(tmpdir(), `cogu-ai-${label}.png`);
  writeFileSync(path, Buffer.from(image.data, 'base64'));
  console.log(`${label}: ${path}`);
}
async function viewport(label, width, height) {
  await command('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 600, screenWidth: width, screenHeight: height });
  const metrics = await evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})');
  if (metrics.scrollWidth > width + 1) throw new Error(`${label} overflow: ${JSON.stringify(metrics)}`);
  await screenshot(label);
}

try {
  const page = await target();
  socket = new WebSocket(page.webSocketDebuggerUrl);
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Runtime.exceptionThrown') console.error('Browser exception:', message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
    if (!message.id) return;
    const waiter = pending.get(message.id); if (!waiter) return; pending.delete(message.id);
    if (message.error) waiter.reject(new Error(message.error.message)); else waiter.resolve(message.result);
  });
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
  await command('Page.enable'); await command('Runtime.enable');
  await command('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await command('Page.navigate', { url: new URL('/shop', base).href });
  await until("document.querySelectorAll('#shop-grid [data-compare-id]').length === 12");
  await evaluate("document.querySelectorAll('#shop-grid [data-compare-id]')[0].click(); document.querySelectorAll('#shop-grid [data-compare-id]')[1].click(); document.querySelector('#compare-go').click()");
  await until("document.querySelectorAll('#compare-result tbody tr').length === 6");
  await evaluate("document.querySelector('#compare-result').scrollIntoView({block:'start',behavior:'instant'})");
  await viewport('compare-desktop', 1440, 900);
  await viewport('compare-tablet', 820, 1180);
  await viewport('compare-mobile', 390, 844);
  await viewport('compare-small-mobile', 320, 720);
  await evaluate("document.querySelector('.cogu-chat-toggle').click(); document.querySelector('#cogu-chat-input').value='Bảng size thế nào?'; document.querySelector('.cogu-chat-form').requestSubmit()");
  await until("document.querySelector('.cogu-chat-messages').textContent.includes('DEMO')");
  await viewport('chat-mobile', 390, 844);
  await command('Page.navigate', { url: new URL('/account', base).href });
  await until("!document.querySelector('#auth-section').hidden");
  await evaluate("(() => { document.querySelector('#register-tab').click(); const f=document.querySelector('#auth-form'); f.elements.name.value='Browser Tester'; f.elements.email.value='ai-browser-'+Date.now()+'@phase7.test'; f.elements.password.value='StrongPassword123!'; f.requestSubmit(); })()");
  await until("!document.querySelector('#shopping-preferences').hidden && document.querySelectorAll('.recommendation-card').length > 0", 15000);
  await evaluate("(() => { const f=document.querySelector('#preferences-form'); f.elements.style.value='toi_gian'; f.elements.budget_vnd.value='1000000'; f.querySelector('input[name=color]').checked=true; f.requestSubmit(); })()");
  await until("document.querySelector('#recommendation-status').textContent.includes('DEMO') && !document.querySelector('#preferences-form button').disabled");
  await evaluate("document.querySelector('#shopping-preferences').scrollIntoView({block:'start',behavior:'instant'})");
  await viewport('recommendations-desktop', 1440, 900);
  await viewport('recommendations-tablet', 820, 1180);
  await viewport('recommendations-mobile', 390, 844);
  await viewport('recommendations-small-mobile', 320, 720);
  console.log('Phase 7 browser QA passed: comparison, chat, saved preferences, live recommendations and four viewport sizes.');
} finally { socket?.close(); chrome.kill(); }
