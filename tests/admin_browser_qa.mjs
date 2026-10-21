// Admin visual and interaction check against a temporary SQLite demo database.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

if (process.env.COGU_BROWSER_QA_TEMP_DB !== '1') throw new Error('Use a temporary COGU_CATALOG_DB and set COGU_BROWSER_QA_TEMP_DB=1.');
const chromePath = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const baseUrl = process.env.COGU_BASE_URL || 'http://127.0.0.1:8765/';
const port = 19225;
const profile = mkdtempSync(join(tmpdir(), 'cogu-admin-browser-'));
const chrome = spawn(chromePath, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-allow-origins=*', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function target() {
  for (let i = 0; i < 60; i++) {
    try { const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); const page = pages.find(item => item.type === 'page'); if (page) return page; }
    catch { /* Starting. */ }
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
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  return result.result.value;
}
async function until(expression, timeout = 9000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try { if (await evaluate(expression)) return; } catch { /* Navigation. */ }
    await pause(120);
  }
  throw new Error(`Timed out: ${expression}; status ${await evaluate("document.querySelector('#admin-status')?.textContent || document.querySelector('#login-status')?.textContent")}`);
}
async function navigate(path) { await command('Page.navigate', { url: new URL(path, baseUrl).href }); }
async function capture(label) {
  const shot = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  const file = join(tmpdir(), `cogu-admin-${label}.png`);
  writeFileSync(file, Buffer.from(shot.data, 'base64'));
  console.log(`${label}: ${file}`);
}
async function viewport(label, width, height, panel) {
  await command('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 600, screenWidth: width, screenHeight: height });
  await navigate('/admin');
  await until("!document.querySelector('#admin-app').hidden");
  if (width < 600) {
    await evaluate("document.querySelector('#admin-menu').click()");
    await until("document.querySelector('#admin-sidebar').classList.contains('is-open') && document.querySelector('#admin-menu').getAttribute('aria-expanded') === 'true'");
  }
  await evaluate(`document.querySelector('#admin-nav [data-view=${panel}]').click()`);
  await until(`!document.querySelector('[data-panel=${panel}]').hidden`);
  if (width < 600 && await evaluate("document.querySelector('#admin-sidebar').classList.contains('is-open')")) throw new Error(`${label}: mobile menu did not close after navigation.`);
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
  await command('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false, screenWidth: 1440, screenHeight: 900 });
  await navigate('/admin');
  await until("!document.querySelector('#admin-login').hidden");
  await capture('login-desktop');
  await evaluate(`document.querySelector('#staff-login-form [name=email]').value='admin@cogu.test'; document.querySelector('#staff-login-form [name=password]').value='DemoPassword123!'; document.querySelector('#staff-login-form').requestSubmit()`);
  await until("!document.querySelector('#admin-app').hidden && document.querySelectorAll('#dashboard-metrics .metric').length === 4");
  await capture('dashboard-desktop');
  await evaluate("document.querySelector('#admin-nav [data-view=products]').click()");
  await until("document.querySelectorAll('#product-rows tr').length >= 30");
  await evaluate("document.querySelector('#new-product').click()");
  const slug = `cogu-browser-admin-${Date.now()}`;
  const sku = `COGU-BROWSER-${Date.now()}`;
  await evaluate(`(() => { const f=document.querySelector('#product-form'); for(const [key,value] of Object.entries({slug:'${slug}',name_vi:'Áo kiểm thử trình duyệt',description_vi:'Sản phẩm dùng để kiểm tra giao diện quản trị.',category:'shirt',material:'Cotton',price_vnd:'390000',image:'images/catalog-17.png'})) f.elements[key].value=value; f.requestSubmit(); })()`);
  await until("!document.querySelector('#variant-management').hidden && document.querySelector('#admin-status').textContent.includes('Đã lưu sản phẩm')");
  await evaluate(`(() => { const f=document.querySelector('#variant-form'); for(const [key,value] of Object.entries({sku:'${sku}',color:'Xanh rừng',size:'M',stock:'3'})) f.elements[key].value=value; f.requestSubmit(); })()`);
  await until(`document.querySelector('#variant-rows').textContent.includes('${sku}')`);
  const stock = await evaluate(`(async () => { const p=await (await fetch('/api/catalog/products/${slug}')).json(); return p.product.variants[0].stock; })()`);
  if (stock !== 3) throw new Error(`Customer catalogue did not receive variant: ${stock}`);
  await capture('product-editor-desktop');
  await evaluate("document.querySelector('#admin-nav [data-view=promotions]').click()");
  await until("document.querySelector('#promotion-list').textContent.includes('COGU10')");
  const code = `BQA${String(Date.now()).slice(-8)}`;
  await evaluate(`(() => {const f=document.querySelector('#promotion-form'); f.elements.code.value='${code}'; f.elements.kind.value='amount'; f.elements.value.value='30000'; f.elements.max_discount_vnd.value='0'; f.elements.min_subtotal_vnd.value='100000'; f.elements.description.value='Mã kiểm thử quản trị'; f.requestSubmit();})()`);
  await until("document.querySelector('#promotion-list').textContent.includes('" + code + "')");
  const active = await evaluate(`(async () => (await (await fetch('/api/promotions')).json()).promotions.some(p => p.code === '${code}'))()`);
  if (!active) throw new Error('Customer promo list did not update.');
  await capture('promotions-desktop');
  for (const [label, width, height] of [['tablet', 820, 1180], ['mobile', 390, 844], ['small-mobile', 320, 720]]) {
    await viewport(`dashboard-${label}`, width, height, 'dashboard');
    await viewport(`products-${label}`, width, height, 'products');
    await viewport(`reports-${label}`, width, height, 'reports');
  }
  await evaluate("document.querySelector('#staff-logout').click()");
  await until("!document.querySelector('#admin-login').hidden");
  await evaluate(`document.querySelector('#staff-login-form [name=email]').value='support@cogu.test'; document.querySelector('#staff-login-form [name=password]').value='DemoPassword123!'; document.querySelector('#staff-login-form').requestSubmit()`);
  await until("!document.querySelector('#admin-app').hidden && !document.querySelector('[data-panel=support]').hidden");
  if (!await evaluate("document.querySelector('#admin-nav [data-view=dashboard]').hidden")) throw new Error('Support dashboard navigation should be hidden.');
  console.log('Admin browser check passed: CRUD, promotion, role-aware navigation and four viewports.');
} finally { socket?.close(); chrome.kill(); }
