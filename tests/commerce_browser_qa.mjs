// Browser journey against an isolated test database. Requires COGU_BROWSER_QA_TEMP_DB=1.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

if (process.env.COGU_BROWSER_QA_TEMP_DB !== '1') throw new Error('Use a server with a temporary COGU_CATALOG_DB and set COGU_BROWSER_QA_TEMP_DB=1.');
const chromePath = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const baseUrl = process.env.COGU_BASE_URL || 'http://127.0.0.1:8765/';
const port = 19224;
const profile = mkdtempSync(join(tmpdir(), 'cogu-commerce-qa-'));
const chrome = spawn(chromePath, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-allow-origins=*', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function target() {
  for (let i = 0; i < 60; i++) {
    try { const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); const page = pages.find(item => item.type === 'page'); if (page) return page; }
    catch { /* Chrome is starting. */ }
    await pause(150);
  }
  throw new Error('Chrome DevTools did not start.');
}
let socket;
let nextId = 0;
const pending = new Map();
function command(method, params = {}) {
  const id = ++nextId;
  return new Promise((resolve, reject) => { pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params })); });
}
async function evaluate(expression) {
  const result = await command('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}
async function until(expression, timeout = 8000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try { if (await evaluate(expression)) return; } catch { /* Navigation. */ }
    await pause(120);
  }
  throw new Error(`Timed out: ${expression}; page status: ${await evaluate("document.querySelector('.commerce-status')?.textContent")}`);
}
async function navigate(path) { await command('Page.navigate', { url: new URL(path, baseUrl).href }); }
async function capture(label) {
  const result = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  const filename = join(tmpdir(), `cogu-commerce-${label}.png`);
  writeFileSync(filename, Buffer.from(result.data, 'base64'));
  console.log(`${label}: ${filename}`);
}
async function viewport(label, width, height, path, ready) {
  await command('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 600, screenWidth: width, screenHeight: height });
  await navigate(path);
  await until(ready);
  const metrics = await evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})');
  if (metrics.scrollWidth > width + 1) throw new Error(`${label} horizontal overflow: ${JSON.stringify(metrics)}`);
  await capture(label);
}

try {
  const page = await target();
  socket = new WebSocket(page.webSocketDebuggerUrl);
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Runtime.exceptionThrown') console.error('Browser exception:', message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
    if (!message.id) return;
    const waiting = pending.get(message.id);
    if (!waiting) return;
    pending.delete(message.id);
    if (message.error) waiting.reject(new Error(message.error.message)); else waiting.resolve(message.result);
  });
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
  await command('Page.enable'); await command('Runtime.enable');
  await viewport('account-desktop', 1440, 900, '/account', "!document.querySelector('#auth-section').hidden");
  await evaluate(`document.querySelector('#register-tab').click(); document.querySelector('#auth-form [name=name]').value='Khách kiểm thử'; document.querySelector('#auth-form [name=email]').value='browser-${Date.now()}@example.test'; document.querySelector('#auth-form [name=password]').value='SafePass123!'; document.querySelector('#auth-form').requestSubmit()`);
  await until("!document.querySelector('#account-section').hidden");
  await evaluate(`(() => {const form=document.querySelector('#address-form'); for(const [name,value] of Object.entries({recipient:'Khách kiểm thử',phone:'0901234567',line1:'12 Nguyễn Huệ',ward:'Bến Nghé',district:'Quận 1',city:'TP HCM'})) form.elements[name].value=value; form.requestSubmit();})()`);
  await until("document.querySelectorAll('#address-list .address-row').length === 1");
  await navigate('/product?slug=ao-thun-oversize-essential');
  await until("!document.querySelector('#product-detail').hidden && !document.querySelector('#add-to-cart').disabled");
  await evaluate("document.querySelector('#add-to-cart').click()");
  await until("document.querySelector('#purchase-status').textContent.includes('Đã thêm')");
  await navigate('/cart');
  await until("!document.querySelector('#cart-content').hidden && document.querySelectorAll('.cart-item').length === 1");
  await evaluate("document.querySelector('#promo-code').value='INVALID-COGU-CODE'; document.querySelector('#promo-form').requestSubmit()");
  await until("document.querySelector('#cart-status').classList.contains('error')");
  if (!await evaluate("document.querySelector('#checkout-button').disabled === false && document.querySelector('#promo-code').value === ''")) throw new Error('Invalid promotion must not block checkout.');
  await capture('cart-desktop');
  await evaluate("document.querySelector('#checkout-form').requestSubmit()");
  await until("location.pathname === '/order' && !document.querySelector('#order-content').hidden");
  const result = await evaluate("({reference:document.querySelector('#order-reference').textContent,states:document.querySelector('#order-states').textContent})");
  if (!result.reference.includes('COGU-') || !result.states.includes('COD')) throw new Error(`Order confirmation failed: ${JSON.stringify(result)}`);
  const orderPath = await evaluate('location.pathname + location.search');
  await capture('order-desktop');
  for (const [label, width, height] of [['tablet', 820, 1180], ['mobile', 390, 844], ['small-mobile', 320, 720]]) {
    await viewport(`account-${label}`, width, height, '/account', "!document.querySelector('#account-section').hidden");
    await viewport(`cart-${label}`, width, height, '/cart', "!document.querySelector('#cart-content').hidden");
    await viewport(`order-${label}`, width, height, orderPath, "!document.querySelector('#order-content').hidden");
  }
  await navigate('/account#orders');
  await until("document.querySelectorAll('#order-list .order-row').length === 1");
  console.log(`Browser purchase journey passed: ${result.reference}; private history persisted across navigation.`);
} finally { socket?.close(); chrome.kill(); }
