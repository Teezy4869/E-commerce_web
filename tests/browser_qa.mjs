// Optional visual and interaction smoke check. Requires local Chrome and a running web server.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const chromePath = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const baseUrl = process.env.COGU_BASE_URL || 'http://127.0.0.1:8765/';
const port = 19223;
const profile = mkdtempSync(join(tmpdir(), 'cogu-browser-qa-'));
const chrome = spawn(chromePath, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-allow-origins=*', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, 'about:blank'
], { windowsHide: true, stdio: 'ignore' });

const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function target() {
  for (let i = 0; i < 60; i++) {
    try {
      const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = targets.find(item => item.type === 'page');
      if (page) return page;
    } catch { /* Chrome is starting. */ }
    await pause(150);
  }
  throw new Error('Chrome DevTools did not start.');
}

let socket;
let commandId = 0;
const pending = new Map();
function command(method, params = {}) {
  const id = ++commandId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const result = await command('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}
async function until(expression, timeout = 7000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try { if (await evaluate(expression)) return; } catch { /* Navigation can replace the context. */ }
    await pause(150);
  }
  throw new Error(`Timed out waiting for: ${expression}`);
}
async function capture(label) {
  const shot = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  const filename = join(tmpdir(), `cogu-qa-${label}.png`);
  writeFileSync(filename, Buffer.from(shot.data, 'base64'));
  return filename;
}

try {
  const page = await target();
  socket = new WebSocket(page.webSocketDebuggerUrl);
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (!message.id) return;
    const waiting = pending.get(message.id);
    if (!waiting) return;
    pending.delete(message.id);
    if (message.error) waiting.reject(new Error(message.error.message));
    else waiting.resolve(message.result);
  });
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true });
    socket.addEventListener('error', reject, { once: true });
  });
  await command('Page.enable');
  await command('Runtime.enable');

  for (const [label, width, height] of [['desktop', 1440, 900], ['tablet', 820, 1180], ['mobile', 390, 844], ['small-mobile', 320, 720]]) {
    await command('Emulation.setDeviceMetricsOverride', {
      width, height, deviceScaleFactor: 1, mobile: width < 600, screenWidth: width, screenHeight: height
    });
    await command('Page.navigate', { url: baseUrl });
    await until("document.querySelectorAll('#catalog-grid .product-card').length === 12");
    const metrics = await evaluate(`({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,menu:getComputedStyle(document.querySelector('#menu-toggle')).display})`);
    if (metrics.width !== width || metrics.scrollWidth > width + 1) {
      throw new Error(`${label}: viewport overflow ${JSON.stringify(metrics)}`);
    }
    if (label === 'mobile' && metrics.menu === 'none') throw new Error('Mobile menu is hidden.');
    const filename = await capture(label);
    console.log(`${label}: 12 products, no horizontal overflow, screenshot ${filename}`);
    for (const [sectionName, selector] of [['callout', '.collection-callout'], ['catalog', '#san-pham'], ['search', '#tim-kiem']]) {
      await evaluate(`window.scrollTo({top:document.querySelector('${selector}').offsetTop-65,behavior:'instant'})`);
      await pause(700);
      await capture(`${label}-${sectionName}`);
    }
    if (label === 'mobile') {
      await evaluate("document.querySelector('#menu-toggle').click()");
      if (!await evaluate("document.querySelector('#primary-nav').classList.contains('is-open')")) throw new Error('Mobile menu did not open.');
      await evaluate("document.querySelector('#primary-nav a').click()");
      if (await evaluate("document.querySelector('#primary-nav').classList.contains('is-open')")) throw new Error('Mobile menu did not close.');
    }
  }

  await evaluate("document.querySelector('[data-category=shirt]').click()");
  if (await evaluate("document.querySelectorAll('#catalog-grid .product-card').length") !== 11) throw new Error('Category filtering failed.');
  await evaluate("document.querySelector('#text-query').value='giày trắng'; document.querySelector('#text-form').requestSubmit()");
  await until("document.querySelectorAll('#results-grid .product-card').length > 0");
  await evaluate("document.querySelector('[data-mode=voice]').click(); document.querySelector('#voice-query').value='giày'; document.querySelector('#voice-form').requestSubmit()");
  await until("document.querySelector('#pipeline-json').textContent.includes('voice_query')");
  await evaluate("document.querySelector('[data-mode=image]').click(); document.querySelector('[data-image=\"images/query_shoes.jpg\"]').click(); document.querySelector('#image-search-button').click()");
  await until("document.querySelector('#pipeline-json').textContent.includes('image_query')");
  await evaluate("document.querySelector('[data-mode=text]').click(); document.querySelector('#text-query').value='áo thun oversize'; document.querySelector('#text-form').requestSubmit()");
  await until("document.querySelector('#results-grid [data-product-id=\"17\"]') !== null");
  await evaluate("document.querySelector('#results-grid [data-product-id=\"17\"]').click()");
  if (!await evaluate("document.querySelector('#product-dialog a[href*=ao-thun-oversize-essential]') !== null")) throw new Error('New catalogue search result has no product detail link.');
  await evaluate("document.querySelector('#dialog-close').click()");
  await evaluate("document.querySelector('#catalog-grid [data-product-id]').click()");
  if (!await evaluate("document.querySelector('#product-dialog').open")) throw new Error('Product details failed.');
  console.log('Interactions: category, Vietnamese text, voice, image and product details passed.');

  for (const [label, width, height] of [['desktop', 1440, 900], ['tablet', 820, 1180], ['mobile', 390, 844], ['small-mobile', 320, 720]]) {
    await command('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 600, screenWidth: width, screenHeight: height });
    await command('Page.navigate', { url: new URL('/shop', baseUrl).href });
    await until("document.querySelectorAll('#shop-grid .product-card').length === 12");
    let metrics = await evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})');
    if (metrics.scrollWidth > width + 1) throw new Error(`${label} shop overflow ${JSON.stringify(metrics)}`);
    console.log(`${label} shop: 12 cards, screenshot ${await capture(`${label}-shop`)}`);
    if (label === 'desktop') {
      const firstPageProduct = await evaluate("document.querySelector('#shop-grid .catalog-card-link').href");
      await evaluate("document.querySelector('#pagination button:nth-child(2)').click()");
      await until("document.querySelector('#shop-count').textContent.includes('Trang 2')");
      if (await evaluate("document.querySelector('#shop-grid .catalog-card-link').href") === firstPageProduct) throw new Error('Shop pagination did not change products.');
      await evaluate("document.querySelector('#shop-sort').value='price_asc'; document.querySelector('#shop-sort').dispatchEvent(new Event('change'))");
      await until("document.querySelectorAll('#shop-grid .product-card').length === 12 && document.querySelector('#shop-grid').getAttribute('aria-busy') === 'false'");
      const prices = await evaluate("[...document.querySelectorAll('#shop-grid .product-price')].map(item => Number(item.textContent.replace(/[^0-9]/g, '')))");
      if (prices.length < 2 || prices.some((price, index) => index > 0 && price < prices[index - 1])) throw new Error('Shop price sort failed.');
    }
    await evaluate("document.querySelector('#filter-category').value='shirt'; document.querySelector('#filter-form').requestSubmit()");
    await until("document.querySelectorAll('#shop-grid .product-card').length === 11");
    if (!await evaluate("document.querySelector('#shop-count').textContent.includes('11 sản phẩm')")) throw new Error('Shop category filter failed.');

    await command('Page.navigate', { url: new URL('/product?slug=ao-thun-oversize-essential', baseUrl).href });
    await until("!document.querySelector('#product-detail').hidden && document.querySelector('#stock-panel').textContent.includes('SKU')");
    metrics = await evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,image:document.querySelector("#gallery-main").naturalWidth})');
    if (metrics.scrollWidth > width + 1 || metrics.image === 0) throw new Error(`${label} product layout/image failed ${JSON.stringify(metrics)}`);
    console.log(`${label} product: loaded, screenshot ${await capture(`${label}-product`)}`);
    await evaluate("[...document.querySelectorAll('#size-options button')].find(b=>b.textContent==='L').click()");
    await until("document.querySelector('#stock-panel').textContent.includes('Tạm hết hàng')");
    await evaluate("document.querySelector('#color-options button:nth-child(2)').click(); [...document.querySelectorAll('#size-options button')].find(b=>b.textContent==='M').click()");
    await until("document.querySelector('#stock-panel').textContent.includes('Còn 14 sản phẩm')");
    if (!await evaluate("document.querySelector('#gallery-main').src.endsWith('catalog-17-ivory.png')")) throw new Error('Gallery did not follow color selection.');
  }
  console.log('Catalogue interactions: filters, product photos, size/color stock passed at four viewports.');
} finally {
  socket?.close();
  chrome.kill();
}
