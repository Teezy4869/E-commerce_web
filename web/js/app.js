(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const state = {
    products: [],
    filter: 'all',
    results: [],
    imageInput: { image_path: 'images/query_shoes.jpg' },
    imageMode: 'demo',
    lastSearch: null,
    recognition: null,
    recording: false,
    requestId: 0,
    catalogSlugs: new Map()
  };
  const categoryNames = { shirt: 'Áo', trousers: 'Quần', shoes: 'Giày/dép' };
  const money = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 });

  function escapeHtml(value) {
    return String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
  }

  function productName(product) { return product.name_vi || product.name; }
  function priceVnd(product) { return Number(product.price_vnd) || 0; }
  function formatPrice(product) { return money.format(priceVnd(product)); }

  async function requestJson(path, options = {}) {
    const response = await fetch(path, options);
    let data;
    try { data = await response.json(); }
    catch { throw new Error(`Máy chủ trả về dữ liệu không hợp lệ (${response.status}).`); }
    if (!response.ok || data.status !== 'success') {
      throw new Error(data.message || `Yêu cầu thất bại (${response.status}).`);
    }
    return data;
  }

  function productCard(product, label = '') {
    const name = escapeHtml(productName(product));
    const category = escapeHtml(categoryNames[product.category] || product.category);
    const image = escapeHtml('/' + String(product.image || '').replace(/^\/+/, ''));
    return `<article class="product-card"><button type="button" data-product-id="${Number(product.id)}" aria-label="Xem chi tiết ${name}">
      <div class="product-image-wrap"><img src="${image}" alt="${name}" loading="lazy">${label ? `<span class="product-badge">${escapeHtml(label)}</span>` : ''}<span class="product-eye" aria-hidden="true">↗</span></div>
      <div class="product-info"><span class="product-category">${category}</span><h3>${name}</h3><span class="product-price">${formatPrice(product)}</span></div>
    </button></article>`;
  }

  function fillGrid(id, products, label = '') {
    const grid = $(id);
    grid.innerHTML = products.length
      ? products.map(product => productCard(product, label)).join('')
      : '<p class="empty-copy">Chưa có sản phẩm trong danh mục này.</p>';
    grid.setAttribute('aria-busy', 'false');
  }

  function variedSelection(products, limit = 4) {
    const selected = [];
    for (const category of ['shirt', 'trousers', 'shoes']) {
      const product = products.find(item => item.category === category);
      if (product) selected.push(product);
    }
    for (const product of products) {
      if (selected.length >= limit) break;
      if (!selected.includes(product)) selected.push(product);
    }
    return selected.slice(0, limit);
  }

  function balancedCatalogue(products, limit = 12) {
    const groups = ['shirt', 'trousers', 'shoes'].map(category => products.filter(item => item.category === category));
    const selected = [];
    for (let index = 0; selected.length < limit && groups.some(group => index < group.length); index++) {
      for (const group of groups) {
        if (group[index] && selected.length < limit) selected.push(group[index]);
      }
    }
    return selected;
  }

  function setFilter(filter) {
    state.filter = filter;
    $$('[data-filter]').forEach(button => {
      const active = button.dataset.filter === filter;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    const matching = filter === 'all' ? state.products : state.products.filter(p => p.category === filter);
    const featured = filter === 'all' ? balancedCatalogue(matching) : matching.slice(0, 12);
    fillGrid('#catalog-grid', featured);
    $('#catalog-count').textContent = `Đang xem ${featured.length}/${matching.length} sản phẩm`;
  }

  function showProduct(id) {
    const product = state.products.find(item => Number(item.id) === id)
      || state.results.find(item => Number(item.product?.id) === id)?.product;
    if (!product) return;
    const name = escapeHtml(productName(product));
    $('#product-dialog-body').innerHTML = `<div class="dialog-content"><img src="/${escapeHtml(product.image)}" alt="${name}"><div class="dialog-copy"><span class="product-category">${escapeHtml(categoryNames[product.category] || product.category)}</span><h2 id="product-dialog-title">${name}</h2><span class="product-price">${formatPrice(product)}</span><p>${escapeHtml(product.description_vi || product.description || '')}</p><div class="dialog-meta">Mã sản phẩm: #${Number(product.id)}<br>Tồn kho hiện tại: ${Number(product.stock) || 0} món. Xem trang sản phẩm để chọn màu và cỡ.</div></div></div>`;
    const slug = product.slug || state.catalogSlugs.get(id);
    if (slug) {
      const link = document.createElement('a');
      link.href = `/product?slug=${encodeURIComponent(slug)}`;
      link.className = 'button button-green';
      link.textContent = 'Xem màu, kích cỡ và tồn kho →';
      $('.dialog-copy', $('#product-dialog-body')).append(link);
    }
    $('#product-dialog').showModal();
  }

  function setMode(mode) {
    $$('[data-mode]').forEach(button => {
      const active = button.dataset.mode === mode;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', String(active));
      button.tabIndex = active ? 0 : -1;
      $(`#panel-${button.dataset.mode}`).hidden = !active;
    });
  }

  function setSearchLoading(message) {
    const section = $('#search-results');
    section.hidden = false;
    section.setAttribute('aria-busy', 'true');
    $('#search-feedback').textContent = message;
    $('#results-grid').innerHTML = '';
  }

  function displayResults(data, title) {
    state.results = data.results || [];
    $('#pipeline-json').textContent = JSON.stringify(data.pipeline || data, null, 2);
    $('#results-title').textContent = title;
    $('#results-mode-label').textContent = data.modality === 'image' ? data.image_label : data.modality === 'voice' ? 'TÌM BẰNG GIỌNG NÓI' : 'TÌM BẰNG TỪ KHÓA';
    $('#sort-results').value = 'relevance';
    $('#search-feedback').textContent = `${state.results.length} sản phẩm phù hợp trong catalogue COGU.${data.image_mode === 'demo' ? ' DEMO: chỉ so khớp vector ảnh mẫu.' : ''}`;
    $('#search-results').setAttribute('aria-busy', 'false');
    renderResults();
  }

  function renderResults() {
    const sort = $('#sort-results').value;
    const items = [...state.results];
    if (sort === 'price-asc') items.sort((a, b) => priceVnd(a.product) - priceVnd(b.product));
    if (sort === 'price-desc') items.sort((a, b) => priceVnd(b.product) - priceVnd(a.product));
    fillGrid('#results-grid', items.map(item => item.product));
    if (!items.length) $('#results-grid').innerHTML = '<p class="empty-copy">Chưa tìm thấy sản phẩm phù hợp. Hãy thử một từ khóa hoặc ảnh mẫu khác.</p>';
  }

  function currentFilters() {
    const form = new FormData($('#search-filters'));
    const filters = {};
    for (const key of ['category', 'color', 'size']) if (form.get(key)) filters[key] = form.get(key);
    for (const key of ['min_price', 'max_price']) if (form.get(key)) filters[key] = Number(form.get(key));
    return filters;
  }

  async function executeSearch(mode, payload, title) {
    state.lastSearch = { mode, payload, title };
    const requestId = ++state.requestId;
    setSearchLoading('Đang tìm sản phẩm…');
    try {
      const data = await requestJson(`/api/search/${mode}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...payload, filters: currentFilters() })
      });
      if (requestId === state.requestId) displayResults(data, title);
    } catch (error) {
      if (requestId !== state.requestId) return;
      $('#search-results').setAttribute('aria-busy', 'false');
      $('#results-title').textContent = 'Không thể tìm kiếm';
      $('#search-feedback').textContent = error.message;
    }
  }

  function setupSpeech() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const button = $('#mic-button');
    if (!SpeechRecognition) {
      button.disabled = true;
      $('#mic-status').textContent = 'Trình duyệt chưa hỗ trợ nhận dạng giọng nói. Hãy nhập nội dung vào ô phía trên.';
      return;
    }
    if (navigator.permissions?.query) {
      navigator.permissions.query({ name: 'microphone' }).then(permission => {
        if (permission.state === 'denied') $('#mic-status').textContent = 'Quyền microphone bị từ chối. Mở quyền trong trình duyệt hoặc nhập nội dung bằng bàn phím.';
        permission.addEventListener?.('change', () => {
          if (permission.state === 'granted') $('#mic-status').textContent = 'Microphone đã được cấp quyền. Bạn có thể nói rồi sửa transcript.';
        });
      }).catch(() => { /* Some browsers do not expose microphone permission state. */ });
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'vi-VN';
    recognition.interimResults = true;
    recognition.continuous = false;
    state.recognition = recognition;
    let speechError = false;
    button.addEventListener('click', () => {
      if (state.recording) { recognition.stop(); return; }
      try { recognition.start(); }
      catch { $('#mic-status').textContent = 'Không thể bật microphone. Kiểm tra quyền truy cập hoặc nhập bằng bàn phím.'; }
    });
    recognition.onstart = () => {
      speechError = false;
      state.recording = true;
      button.setAttribute('aria-pressed', 'true');
      $('span', button).textContent = 'Dừng ghi âm';
      $('#mic-status').textContent = 'Đang nghe tiếng Việt… Bạn có thể dừng và sửa nội dung trước khi tìm.';
    };
    recognition.onresult = event => {
      const transcript = [...event.results].map(result => result[0]?.transcript || '').join(' ').trim();
      if (!transcript) return;
      $('#voice-query').value = transcript;
      $('#mic-status').textContent = 'Đã ghi transcript. Hãy kiểm tra, sửa nếu cần rồi chọn “Tìm sản phẩm”.';
    };
    recognition.onerror = event => {
      speechError = true;
      const messages = {
        'not-allowed': 'Quyền microphone bị từ chối. Hãy cấp quyền hoặc nhập nội dung bằng bàn phím.',
        'service-not-allowed': 'Dịch vụ nhận dạng giọng nói không được cấp quyền. Hãy nhập nội dung bằng bàn phím.',
        'no-speech': 'Chưa nghe rõ tiếng nói. Bạn có thể thử lại hoặc nhập bằng bàn phím.',
        'audio-capture': 'Không tìm thấy microphone. Hãy nhập nội dung bằng bàn phím.',
        network: 'Dịch vụ nhận dạng chưa kết nối. Hãy nhập nội dung bằng bàn phím.'
      };
      $('#mic-status').textContent = messages[event.error] || 'Không thể nhận dạng giọng nói. Hãy nhập nội dung bằng bàn phím.';
    };
    recognition.onend = () => {
      state.recording = false;
      button.setAttribute('aria-pressed', 'false');
      $('span', button).textContent = 'Dùng microphone';
      if (!speechError && $('#voice-query').value.trim()) $('#voice-query').focus();
    };
  }

  function renderOrder(order) {
    if (!order) { $('#order-output').textContent = 'Không tìm thấy đơn hàng.'; return; }
    $('#order-output').innerHTML = `<p><strong>${escapeHtml(order.order_id)}</strong> · ${escapeHtml(order.status)}<br>Khách hàng: ${escapeHtml(order.customer_id)}<br>Ngày: ${escapeHtml(order.date)}<br>Tổng tiền trong dữ liệu gốc: ${escapeHtml(order.total)}</p>`;
  }

  function setupEvents() {
    const menu = $('#primary-nav');
    const menuButton = $('#menu-toggle');
    menuButton.addEventListener('click', () => {
      const open = menu.classList.toggle('is-open');
      menuButton.setAttribute('aria-expanded', String(open));
      menuButton.setAttribute('aria-label', open ? 'Đóng menu' : 'Mở menu');
    });
    $$('#primary-nav a').forEach(link => link.addEventListener('click', () => {
      menu.classList.remove('is-open');
      menuButton.setAttribute('aria-expanded', 'false');
      menuButton.setAttribute('aria-label', 'Mở menu');
    }));
    $$('[data-category]').forEach(button => button.addEventListener('click', () => {
      setFilter(button.dataset.category);
      $('#san-pham').scrollIntoView({ behavior: 'smooth' });
    }));
    $$('[data-filter]').forEach(button => button.addEventListener('click', () => setFilter(button.dataset.filter)));
    document.addEventListener('click', event => {
      const card = event.target.closest('[data-product-id]');
      if (card) showProduct(Number(card.dataset.productId));
    });
    $('#dialog-close').addEventListener('click', () => $('#product-dialog').close());
    $('#product-dialog').addEventListener('click', event => {
      if (event.target === $('#product-dialog')) $('#product-dialog').close();
    });
    const searchTabs = $$('[data-mode]');
    searchTabs.forEach((tab, index) => {
      tab.addEventListener('click', () => setMode(tab.dataset.mode));
      tab.addEventListener('keydown', event => {
        let next = null;
        if (event.key === 'ArrowRight') next = (index + 1) % searchTabs.length;
        if (event.key === 'ArrowLeft') next = (index - 1 + searchTabs.length) % searchTabs.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = searchTabs.length - 1;
        if (next === null) return;
        event.preventDefault();
        setMode(searchTabs[next].dataset.mode);
        searchTabs[next].focus();
      });
    });
    setMode('text');
    $$('[data-open-mode]').forEach(link => link.addEventListener('click', () => setMode(link.dataset.openMode)));
    $('#text-form').addEventListener('submit', event => {
      event.preventDefault();
      const text = $('#text-query').value.trim();
      if (text) executeSearch('text', { text }, `Kết quả cho “${text}”`);
    });
    $('#voice-form').addEventListener('submit', event => {
      event.preventDefault();
      const transcript = $('#voice-query').value.trim();
      if (transcript) executeSearch('voice', { audio_input: transcript }, `Kết quả cho “${transcript}”`);
    });
    $$('[data-image]').forEach(button => button.addEventListener('click', () => {
      $$('[data-image]').forEach(item => {
        const selected = item === button;
        item.classList.toggle('is-active', selected);
        item.setAttribute('aria-pressed', String(selected));
      });
      $('#image-file').value = '';
      state.imageInput = { image_path: button.dataset.image };
      $('#image-selection').textContent = `Đang chọn: ${$('span', button).textContent} mẫu${state.imageMode === 'demo' ? ' · DEMO' : ''}`;
    }));
    $('#image-file').addEventListener('change', event => {
      const file = event.target.files?.[0];
      if (!file) return;
      if (state.imageMode !== 'encoder') {
        $('#image-selection').textContent = 'DEMO chỉ hỗ trợ ảnh giày mẫu; ảnh tải lên cần bộ mã hóa ảnh.';
        event.target.value = '';
        return;
      }
      if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
        $('#image-selection').textContent = 'Hãy chọn ảnh PNG, JPEG hoặc WebP dưới 5 MB.';
        event.target.value = '';
        return;
      }
      $$('[data-image]').forEach(item => { item.classList.remove('is-active'); item.setAttribute('aria-pressed', 'false'); });
      state.imageInput = null;
      $('#image-search-button').disabled = true;
      $('#image-selection').textContent = `Đang đọc nội dung ${file.name}…`;
      const reader = new FileReader();
      reader.onload = () => {
        const data = String(reader.result || '');
        const match = /^data:image\/(?:png|jpeg|webp);base64,([A-Za-z0-9+/=]+)$/.exec(data);
        if (!match) { $('#image-selection').textContent = 'Không đọc được ảnh. Hãy chọn ảnh khác.'; return; }
        state.imageInput = { image_data: match[1] };
        $('#image-search-button').disabled = false;
        $('#image-selection').textContent = `${file.name} · ảnh sẵn sàng để tìm theo nội dung`;
      };
      reader.onerror = () => { $('#image-selection').textContent = 'Không đọc được ảnh. Hãy chọn ảnh khác.'; };
      reader.readAsDataURL(file);
    });
    $('#image-search-button').addEventListener('click', () => {
      if (state.imageInput) executeSearch('image', state.imageInput, 'Sản phẩm tương tự');
    });
    $('#sort-results').addEventListener('change', renderResults);
    $('#search-filters').addEventListener('submit', event => {
      event.preventDefault();
      if (state.lastSearch) executeSearch(state.lastSearch.mode, state.lastSearch.payload, state.lastSearch.title);
    });
    $('#reset-search-filters').addEventListener('click', () => {
      $('#search-filters').reset();
      if (state.lastSearch) executeSearch(state.lastSearch.mode, state.lastSearch.payload, state.lastSearch.title);
    });
    $('#order-form').addEventListener('submit', async event => {
      event.preventDefault();
      const token = $('#admin-token').value;
      const orderId = $('#order-id').value.trim();
      $('#order-output').textContent = 'Đang tra cứu…';
      try {
        const data = await requestJson('/api/search/order', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token }, body: JSON.stringify({ order_id: orderId }) });
        renderOrder(data.order);
      } catch (error) { $('#order-output').textContent = error.message; }
    });
    $('#load-orders').addEventListener('click', async () => {
      const token = $('#admin-token').value;
      if (!token) { $('#order-output').textContent = 'Nhập mã quản trị trước.'; return; }
      $('#order-output').textContent = 'Đang tải…';
      try {
        const data = await requestJson('/api/orders', { headers: { 'X-Admin-Token': token } });
        $('#order-output').innerHTML = `<table><thead><tr><th>Mã</th><th>Trạng thái</th><th>Khách hàng</th></tr></thead><tbody>${data.orders.map(order => `<tr><td>${escapeHtml(order.order_id)}</td><td>${escapeHtml(order.status)}</td><td>${escapeHtml(order.customer_id)}</td></tr>`).join('')}</tbody></table>`;
      } catch (error) { $('#order-output').textContent = error.message; }
    });
    setupSpeech();
  }

  async function init() {
    setupEvents();
    requestJson('/api/search/capabilities').then(data => {
      state.imageMode = data.image_mode;
      $('#image-mode-label').textContent = data.image_label;
      $('#image-mode-notice').textContent = data.image_mode === 'demo'
        ? 'DEMO: chỉ dùng ảnh giày mẫu với vector định sẵn; chưa phân tích nội dung ảnh tải lên.'
        : data.image_notice;
      $('#image-file').disabled = !data.upload_enabled;
      $('#image-file').hidden = !data.upload_enabled;
      $('#image-upload-label').hidden = !data.upload_enabled;
      $('#image-selection').textContent = data.upload_enabled ? 'Đang chọn: Giày mẫu' : 'Đang chọn: Giày mẫu · DEMO';
    }).catch(() => { $('#image-mode-notice').textContent = 'DEMO: chỉ dùng ảnh giày mẫu; chưa kết nối được cấu hình mã hóa ảnh.'; });
    requestJson('/api/catalog/facets').then(data => {
      for (const [name, values] of [['color', data.colors], ['size', data.sizes]]) {
        const select = $('#search-filters').elements[name];
        for (const value of values || []) select.add(new Option(value, value));
      }
    }).catch(() => {});
    try {
      const data = await requestJson('/api/catalog/products?page_size=48');
      state.products = data.products || [];
      state.catalogSlugs = new Map(state.products.map(product => [Number(product.id), product.slug]));
      fillGrid('#new-grid', variedSelection(state.products.filter(p => p.is_new)), 'MỚI');
      fillGrid('#best-grid', variedSelection(state.products.filter(p => p.is_bestseller)), 'NỔI BẬT');
      setFilter('all');
    } catch (error) {
      ['#new-grid', '#best-grid', '#catalog-grid'].forEach(id => { $(id).innerHTML = `<p class="empty-copy">${escapeHtml(error.message)}</p>`; $(id).setAttribute('aria-busy', 'false'); });
      $('#catalog-count').textContent = 'Không tải được';
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
