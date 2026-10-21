(() => {
  'use strict';
  const money = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 });
  const names = { shirt: 'Áo', trousers: 'Quần', shoes: 'Giày/dép' };
  const escape = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
  const imageUrl = path => '/' + String(path || '').replace(/^\/+/, '');
  async function json(url) {
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok || data.status !== 'success') throw new Error(data.message || `Yêu cầu thất bại (${response.status})`);
    return data;
  }
  function card(product, eager = false) {
    const name = escape(product.name_vi);
    const label = product.is_new ? 'MỚI' : product.is_bestseller ? 'NỔI BẬT' : '';
    return `<article class="product-card"><a class="catalog-card-link" href="/product?slug=${encodeURIComponent(product.slug)}" aria-label="Xem ${name}">
      <div class="product-image-wrap"><img src="${escape(imageUrl(product.image))}" alt="${name}" loading="${eager ? 'eager' : 'lazy'}">${label ? `<span class="product-badge">${label}</span>` : ''}<span class="product-eye" aria-hidden="true">↗</span></div>
      <div class="product-info"><span class="product-category">${escape(names[product.category] || product.category)}</span><h3>${name}</h3><span class="product-price">${money.format(product.price_vnd)}</span><small class="card-stock">${product.stock > 0 ? 'Còn hàng' : 'Hết hàng'}</small></div>
    </a></article>`;
  }
  const menu = document.querySelector('#primary-nav');
  const toggle = document.querySelector('#menu-toggle');
  if (menu && toggle) {
    toggle.addEventListener('click', () => {
      const open = menu.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    menu.addEventListener('click', event => {
      if (event.target.closest('a')) { menu.classList.remove('is-open'); toggle.setAttribute('aria-expanded', 'false'); }
    });
  }
  window.CoguCatalog = { money, names, escape, imageUrl, json, card };
})();
