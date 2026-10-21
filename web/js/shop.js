(() => {
  'use strict';
  const { json, card, escape } = window.CoguCatalog;
  const $ = selector => document.querySelector(selector);
  const fields = { q: '#filter-q', category: '#filter-category', color: '#filter-color', size: '#filter-size', min_price: '#filter-min', max_price: '#filter-max', sort: '#shop-sort' };
  let page = 1;
  let requestId = 0;

  function currentParams() {
    const params = new URLSearchParams();
    for (const [key, selector] of Object.entries(fields)) {
      const value = $(selector).value.trim();
      if (value && !(key === 'sort' && value === 'newest')) params.set(key, value);
    }
    params.set('page', String(page));
    params.set('page_size', '12');
    return params;
  }
  async function load(updateUrl = true) {
    const id = ++requestId;
    const params = currentParams();
    $('#shop-grid').setAttribute('aria-busy', 'true');
    $('#shop-grid').innerHTML = '<p class="loading-copy">Đang tải sản phẩm…</p>';
    $('#shop-count').textContent = 'Đang tải sản phẩm…';
    if (updateUrl) history.replaceState(null, '', '/shop?' + params.toString());
    try {
      const data = await json('/api/catalog/products?' + params);
      if (id !== requestId) return;
      $('#shop-grid').innerHTML = data.products.length ? data.products.map((product, index) =>
        card(product, index < 3).replace('</article>', `<button type="button" class="compare-pick" data-compare-id="${product.id}" data-compare-name="${escape(product.name_vi)}" aria-pressed="false">+ So sánh</button></article>`)).join('') : '<p class="empty-copy">Không tìm thấy sản phẩm phù hợp. Hãy thử bộ lọc khác.</p>';
      document.querySelector('#compare-count')?.dispatchEvent(new Event('cogu:refresh-selection'));
      $('#shop-grid').setAttribute('aria-busy', 'false');
      $('#shop-count').textContent = `${data.total} sản phẩm · Trang ${data.page}${data.pages ? ` / ${data.pages}` : ''}`;
      const pagination = $('#pagination');
      pagination.innerHTML = '';
      if (data.pages > 1) {
        for (let number = 1; number <= data.pages; number++) {
          const button = document.createElement('button');
          button.type = 'button'; button.textContent = String(number);
          button.setAttribute('aria-label', `Trang ${number}`);
          if (number === data.page) button.setAttribute('aria-current', 'page');
          button.addEventListener('click', () => { page = number; load(); window.scrollTo({ top: $('#main').offsetTop, behavior: 'smooth' }); });
          pagination.append(button);
        }
      }
    } catch (error) {
      if (id !== requestId) return;
      $('#shop-grid').setAttribute('aria-busy', 'false');
      $('#shop-grid').innerHTML = `<p class="empty-copy">${escape(error.message)}</p>`;
      $('#shop-count').textContent = 'Không thể tải sản phẩm';
    }
  }
  async function facets() {
    try {
      const data = await json('/api/catalog/facets');
      for (const [key, values] of [['color', data.colors], ['size', data.sizes]]) {
        const select = $(fields[key]);
        const selected = new URLSearchParams(location.search).get(key) || '';
        for (const value of values) select.add(new Option(value, value));
        select.value = selected;
      }
    } catch { /* Products can still load without facet suggestions. */ }
  }
  const fromUrl = new URLSearchParams(location.search);
  for (const [key, selector] of Object.entries(fields)) {
    if (key === 'color' || key === 'size') continue;
    const value = fromUrl.get(key);
    if (value) $(selector).value = value;
  }
  const requestedPage = Number(fromUrl.get('page'));
  page = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;
  $('#filter-form').addEventListener('submit', event => { event.preventDefault(); page = 1; load(); });
  $('#shop-sort').addEventListener('change', () => { page = 1; load(); });
  $('#clear-filters').addEventListener('click', () => {
    $('#filter-form').reset(); $('#shop-sort').value = 'newest'; page = 1; load();
  });
  $('#mobile-filter-toggle').addEventListener('click', () => {
    const open = $('.shop-sidebar').classList.toggle('is-open');
    $('#mobile-filter-toggle').setAttribute('aria-expanded', String(open));
  });
  if ([...fromUrl.keys()].some(key => !['page', 'page_size', 'sort'].includes(key))) {
    $('.shop-sidebar').classList.add('is-open');
    $('#mobile-filter-toggle').setAttribute('aria-expanded', 'true');
  }
  facets().then(() => load(false));
})();
