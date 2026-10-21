// Phase 6 browser interactions. Run against a server with a temporary demo database.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

if (process.env.COGU_BROWSER_QA_TEMP_DB !== '1') throw new Error('Use a temporary COGU_CATALOG_DB and set COGU_BROWSER_QA_TEMP_DB=1.');
const baseUrl = process.env.COGU_BASE_URL || 'http://127.0.0.1:8765/';
const chromePath = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const port = 19226;
const chrome = spawn(chromePath, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-allow-origins=*', `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'cogu-search-browser-'))}`, 'about:blank'],
{ windowsHide: true, stdio: 'ignore' });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket;
let serial = 0;
const pending = new Map();
async function target() {
  for (let i = 0; i < 60; i++) {
    try {
      const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = pages.find(item => item.type === 'page');
      if (page) return page;
    } catch { /* Chrome is starting. */ }
    await pause(150);
  }
  throw new Error('Chrome DevTools did not start.');
}
function command(method, params = {}) {
  const id = ++serial;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const response = await command('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
  if (response.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text);
  return response.result.value;
}
async function until(expression, timeout = 10000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try { if (await evaluate(expression)) return; } catch { /* Navigation. */ }
    await pause(100);
  }
  throw new Error(`Timed out: ${expression}; ${JSON.stringify(await evaluate("({feedback:document.querySelector('#search-feedback')?.textContent,pipeline:document.querySelector('#pipeline-json')?.textContent.slice(0,100),ids:[...document.querySelectorAll('#results-grid [data-product-id]')].map(x=>x.dataset.productId)})"))}`);
}
async function screenshot(label) {
  const result = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  const path = join(tmpdir(), `cogu-search-${label}.png`);
  writeFileSync(path, Buffer.from(result.data, 'base64'));
  console.log(`${label}: ${path}`);
}

try {
  const page = await target();
  socket = new WebSocket(page.webSocketDebuggerUrl);
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Runtime.exceptionThrown') console.error('Browser exception:', message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
    if (!message.id) return;
    const waiter = pending.get(message.id);
    if (!waiter) return;
    pending.delete(message.id);
    if (message.error) waiter.reject(new Error(message.error.message)); else waiter.resolve(message.result);
  });
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true });
    socket.addEventListener('error', reject, { once: true });
  });
  await command('Page.enable');
  await command('Runtime.enable');
  await command('Page.addScriptToEvaluateOnNewDocument', { source: `
    window.SpeechRecognition = class {
      start() {
        this.onstart?.();
        this.onresult?.({ results: [[{ transcript: 'giay trang' }]] });
        this.onend?.();
      }
      stop() { this.onend?.(); }
    };
  ` });
  await command('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await command('Page.navigate', { url: baseUrl });
  await until("document.querySelector('#image-mode-label').textContent.includes('DEMO')");
  await until("document.querySelectorAll('#catalog-grid .product-card').length === 12");
  if (!await evaluate("document.querySelector('#image-file').disabled")) throw new Error('Unconfigured image upload must be disabled.');
  await evaluate("document.querySelector('#text-query').value='áo thun oversize'; document.querySelector('#text-form').requestSubmit()");
  await until(`document.querySelector('#results-grid [data-product-id="17"]') !== null`);
  const accentedTop = await evaluate("document.querySelector('#results-grid [data-product-id]')?.dataset.productId");
  await evaluate("document.querySelector('#text-query').value='ao thun oversize'; document.querySelector('#text-form').requestSubmit()");
  await until(`document.querySelector('#results-grid [data-product-id="17"]') !== null && document.querySelector('#pipeline-json').textContent.includes('ao thun oversize')`);
  const plainTop = await evaluate("document.querySelector('#results-grid [data-product-id]')?.dataset.productId");
  if (accentedTop !== plainTop) throw new Error('Accent folding changed the best match.');
  await evaluate("document.querySelector('#search-filters [name=category]').value='shirt'; document.querySelector('#search-filters [name=size]').value='M'; document.querySelector('#search-filters').requestSubmit()");
  await until(`document.querySelector('#pipeline-json').textContent.includes('"category": "shirt"')`);
  if (!await evaluate(`document.querySelector('#results-grid [data-product-id="17"]') !== null`)) throw new Error('Filtered text search lost the matching shirt.');
  await evaluate("document.querySelector('#search-results').scrollIntoView({block:'start',behavior:'instant'})");
  await until("document.querySelector('#results-grid img')?.naturalWidth > 0");
  await screenshot('text-desktop');
  await evaluate("document.querySelector('#reset-search-filters').click(); document.querySelector('[data-mode=voice]').click(); document.querySelector('#mic-button').click()");
  await until("document.querySelector('#voice-query').value === 'giay trang'");
  if (await evaluate("document.querySelector('#pipeline-json').textContent.includes('voice_query')")) throw new Error('Voice recognition searched before transcript confirmation.');
  await evaluate("document.querySelector('#voice-query').value='giày trắng'; document.querySelector('#voice-form').requestSubmit()");
  await until("document.querySelector('#pipeline-json').textContent.includes('voice_query') && document.querySelectorAll('#results-grid .product-card').length > 0");
  await evaluate("document.querySelector('#search-results').scrollIntoView({block:'start',behavior:'instant'})");
  await screenshot('voice-desktop');
  await evaluate("document.querySelector('[data-mode=image]').click(); document.querySelector('[data-image=\"images/query_shoes.jpg\"]').click(); document.querySelector('#image-search-button').click()");
  await until("document.querySelector('#results-mode-label').textContent.includes('DEMO') && document.querySelector('#pipeline-json').textContent.includes('image_query')");
  await evaluate("document.querySelector('#search-results').scrollIntoView({block:'start',behavior:'instant'})");
  await screenshot('image-demo-desktop');
  for (const [label, width, height] of [['tablet', 820, 1180], ['mobile', 390, 844], ['small-mobile', 320, 720]]) {
    await command('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 600, screenWidth: width, screenHeight: height });
    const metrics = await evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})');
    if (metrics.scrollWidth > width + 1) throw new Error(`${label}: horizontal overflow ${JSON.stringify(metrics)}`);
    await evaluate("document.querySelector('#search-results').scrollIntoView({block:'start',behavior:'instant'})");
    await screenshot(label);
  }
  console.log('Phase 6 browser QA passed: accent folding, filters, editable Vietnamese voice transcript, explicit image DEMO and responsive results.');
} finally {
  socket?.close();
  chrome.kill();
}
