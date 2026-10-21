// AI Studio end-to-end browser check. Use a temporary COGU_CATALOG_DB.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

if (process.env.COGU_BROWSER_QA_TEMP_DB !== '1') throw new Error('Use a temporary COGU_CATALOG_DB and set COGU_BROWSER_QA_TEMP_DB=1.');
const base = process.env.COGU_BASE_URL || 'http://127.0.0.1:8765/';
const port = 19228;
const chrome = spawn(process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-allow-origins=*',
    `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'cogu-studio-browser-'))}`, 'about:blank'],
  { windowsHide: true, stdio: 'ignore' });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket; let serial = 0; const pending = new Map();
async function target() {
  for (let i = 0; i < 60; i++) {
    try { const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); const page = pages.find(item => item.type === 'page'); if (page) return page; }
    catch { /* Browser starting. */ }
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
async function until(expression, timeout = 12000) {
  const start = Date.now();
  while (Date.now() - start < timeout) { try { if (await evaluate(expression)) return; } catch { /* Navigation. */ } await sleep(120); }
  throw new Error(`Timed out: ${expression}; ${JSON.stringify(await evaluate("({status:document.querySelector('#studio-status')?.textContent,mode:document.querySelector('#studio-mode')?.textContent})"))}`);
}
async function capture(label) {
  const shot = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  const path = join(tmpdir(), `cogu-studio-${label}.png`);
  writeFileSync(path, Buffer.from(shot.data, 'base64'));
  console.log(`${label}: ${path}`);
}
async function viewport(label, width, height) {
  await command('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 600, screenWidth: width, screenHeight: height });
  const metrics = await evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})');
  if (metrics.scrollWidth > width + 1) throw new Error(`${label} overflow: ${JSON.stringify(metrics)}`);
  await evaluate("document.querySelector('#studio-builder').scrollIntoView({block:'start',behavior:'instant'})");
  await capture(label);
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
  await command('Page.navigate', { url: new URL('/studio', base).href });
  await until("document.querySelector('#studio-shirt option:nth-child(2)') !== null && document.querySelector('#studio-shoes option:nth-child(2)') !== null");
  if (await evaluate("document.querySelectorAll('#studio-form input[type=file]').length !== 0")) throw new Error('Studio unexpectedly requests a personal photo.');
  if (await evaluate("document.querySelectorAll('#studio-form [name=body_type]').length !== 5")) throw new Error('Studio body types are incomplete.');
  if (await evaluate("document.querySelectorAll('#studio-form [name=gender]').length !== 2")) throw new Error('Studio gender choices are incomplete.');
  if (await evaluate("!document.querySelector('#studio-submit').disabled")) throw new Error('Empty outfit can be submitted.');
  await evaluate("(async () => { const response=await fetch('/api/auth/register',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:'studio-browser-'+Date.now()+'@phase8.test',name:'Studio Browser',password:'StrongPassword123!'})}); if (!response.ok) throw new Error('Cannot create test customer'); })()");
  await evaluate("(() => { const f=document.querySelector('#studio-form'); for (const name of ['shirt','trousers','shoes']) { f.elements[name].selectedIndex=1; f.elements[name].dispatchEvent(new Event('change')); } f.querySelector('[value=female]').click(); f.querySelector('[value=petite]').click(); f.requestSubmit(); })()");
  await until("document.querySelector('#studio-mode').textContent.includes('DEMO') && document.querySelector('#studio-image').src.includes('outfit-sample-female-petite') && document.querySelectorAll('#studio-selected a').length === 3 && document.querySelector('#studio-progress').hidden");
  await until("document.querySelector('#studio-image').naturalWidth > 0");
  if (!await evaluate("document.querySelector('#studio-status').textContent.includes('không dùng sản phẩm đã chọn')")) throw new Error('Sample disclosure is missing.');
  await viewport('desktop', 1440, 900);
  await viewport('tablet', 820, 1180);
  await viewport('mobile', 390, 844);
  await evaluate("document.querySelector('.studio-output').scrollIntoView({block:'start',behavior:'instant'})");
  await capture('mobile-preview');
  await viewport('small-mobile', 320, 720);
  await evaluate("document.querySelector('.studio-output').scrollIntoView({block:'start',behavior:'instant'})");
  await capture('small-mobile-preview');
  await evaluate("(() => { const f=document.querySelector('#studio-form'); f.elements.trousers.value=''; f.elements.trousers.dispatchEvent(new Event('change')); f.elements.shoes.value=''; f.elements.shoes.dispatchEvent(new Event('change')); f.querySelector('[value=male]').click(); f.querySelector('[value=curvy]').click(); f.requestSubmit(); })()");
  await until("document.querySelector('#studio-image').src.includes('outfit-sample-male-curvy') && document.querySelectorAll('#studio-selected a').length === 1 && document.querySelector('#studio-progress').hidden");
  console.log('Studio browser QA passed: catalogue selection, two genders, five body types, sample disclosures, result reset and four responsive viewports.');
} finally { socket?.close(); chrome.kill(); }
