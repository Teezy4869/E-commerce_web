(() => {
  'use strict';
  const { money, escape } = window.CoguCatalog;
  const $ = selector => document.querySelector(selector);
  const form = $('#studio-form');
  const button = $('#studio-submit');
  const categories = ['shirt', 'trousers', 'shoes'];
  let catalogue = {};
  let busy = false;

  function selected() {
    return Object.fromEntries(categories.filter(category => form.elements[category].value)
      .map(category => [category, Number(form.elements[category].value)]));
  }
  function bodyType() { return form.elements.body_type.value; }
  function gender() { return form.elements.gender.value; }
  function sample(body = bodyType(), modelGender = gender()) { return `/images/outfit-sample-${modelGender}-${body}.png`; }
  function status(message, error = false) {
    $('#studio-status').textContent = message;
    $('#studio-status').classList.toggle('error', error);
  }
  function showSample(message) {
    $('#studio-image').src = sample();
    $('#studio-image').alt = `Ảnh mẫu minh họa người mẫu ${gender() === 'male' ? 'nam' : 'nữ'}, dáng ${bodyType()}; không dùng sản phẩm đã chọn`;
    $('#studio-mode').textContent = 'DEMO · ẢNH MẪU';
    $('#studio-image-mark').hidden = false;
    $('#studio-selected').replaceChildren();
    status(message);
  }
  function updatePick(category) {
    const id = Number(form.elements[category].value);
    const product = (catalogue[category] || []).find(item => item.id === id);
    const container = $(`#studio-${category}-detail`);
    if (!product) {
      container.innerHTML = `<p>${{ shirt: 'Chọn một chiếc áo từ COGU.', trousers: 'Chọn một chiếc quần từ COGU.', shoes: 'Chọn một đôi giày/dép từ COGU.' }[category]}</p>`;
      return;
    }
    container.innerHTML = `<div class="studio-picked"><img src="/${escape(product.image)}" alt="" loading="lazy"><div><strong>${escape(product.name_vi)}</strong><small>${money.format(product.price_vnd)} · ${product.stock} sản phẩm trên các biến thể</small><a href="/product?slug=${encodeURIComponent(product.slug)}">Xem màu và cỡ →</a></div></div>`;
  }
  function updateForm() {
    for (const category of categories) updatePick(category);
    const count = Object.keys(selected()).length;
    button.disabled = busy || count === 0;
    $('#studio-selection-note').textContent = count ? `Đã chọn ${count}/3 danh mục. Ảnh sẽ được tạo sau khi bạn nhấn nút.` : 'Chọn ít nhất một sản phẩm để bắt đầu.';
  }
  function resetPreview() {
    showSample('Lựa chọn đã thay đổi. Ảnh đang hiển thị chỉ là mẫu minh họa; hãy tạo ảnh mới để xem bản cập nhật.');
    updateForm();
  }
  for (const category of categories) form.elements[category].addEventListener('change', resetPreview);
  form.querySelectorAll('[name=body_type]').forEach(input => input.addEventListener('change', resetPreview));
  form.querySelectorAll('[name=gender]').forEach(input => input.addEventListener('change', resetPreview));

  async function loadCatalog() {
    status('Đang tải áo, quần và giày từ catalogue…');
    try {
      const response = await fetch('/api/outfit/catalog', { credentials: 'same-origin' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Không thể tải catalogue.');
      catalogue = data.products;
      for (const category of categories) {
        const select = form.elements[category];
        const title = data.categories[category];
        select.innerHTML = `<option value="">Không chọn ${escape(title.toLowerCase())}</option>` +
          catalogue[category].map(item => `<option value="${item.id}">${escape(item.name_vi)} · ${money.format(item.price_vnd)}</option>`).join('');
        if (!catalogue[category].length) select.disabled = true;
      }
      $('#studio-disclaimer').textContent = data.disclaimer;
      status(data.image_mode === 'provider'
        ? 'Dịch vụ tạo ảnh đã cấu hình. Chọn sản phẩm và dáng người để xem bản mô phỏng.'
        : 'DEMO: chưa cấu hình dịch vụ tạo ảnh. Studio sẽ hiển thị ảnh mẫu của dáng người, không theo sản phẩm đã chọn.');
      updateForm();
    } catch (error) { status(error.message, true); button.disabled = true; }
  }

  async function csrfToken() {
    try {
      const response = await fetch('/api/auth/me', { credentials: 'same-origin' });
      return response.ok ? (await response.json()).csrf_token || '' : '';
    } catch { return ''; }
  }
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const products = selected();
    const selectedBodyType = bodyType();
    const selectedGender = gender();
    if (busy || !Object.keys(products).length) return;
    busy = true; button.disabled = true;
    form.querySelectorAll('select,input').forEach(control => { control.disabled = true; });
    $('#studio-progress').hidden = false;
    $('#studio-progress-text').textContent = 'Đang kiểm tra sản phẩm trong catalogue.';
    status('Đang chuẩn bị bản xem trước…');
    const messages = ['Đang gửi ảnh tham chiếu sản phẩm tới dịch vụ tạo ảnh (nếu đã cấu hình).',
                      'Đang chờ ảnh mô phỏng. Quá trình này có thể mất khoảng một phút.'];
    let step = 0;
    const timer = setInterval(() => { $('#studio-progress-text').textContent = messages[Math.min(step++, messages.length - 1)]; }, 3500);
    try {
      const csrf = await csrfToken();
      const headers = { 'Content-Type': 'application/json' };
      if (csrf) headers['X-CSRF-Token'] = csrf;
      const response = await fetch('/api/outfit/preview', { method: 'POST', credentials: 'same-origin', headers,
        body: JSON.stringify({ body_type: selectedBodyType, gender: selectedGender, products }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Không thể tạo bản xem trước.');
      const nextImage = new Image(); nextImage.src = data.image_url;
      await nextImage.decode();
      $('#studio-image').src = data.image_url;
      $('#studio-image').alt = data.mode === 'provider'
        ? `Ảnh AI mô phỏng người mẫu ${data.gender === 'male' ? 'nam' : 'nữ'}, dáng ${data.body_type} với ${data.products.map(item => item.name_vi).join(', ')}`
        : `Ảnh mẫu minh họa người mẫu ${data.gender === 'male' ? 'nam' : 'nữ'}, dáng ${data.body_type}; không dùng sản phẩm đã chọn`;
      $('#studio-mode').textContent = data.label;
      $('#studio-image-mark').hidden = data.mode === 'provider';
      $('#studio-disclaimer').textContent = data.disclaimer;
      $('#studio-selected').innerHTML = '<h3>Sản phẩm đã chọn từ catalogue</h3>' + data.products.map(item =>
        `<a href="/product?slug=${encodeURIComponent(item.slug)}"><strong>${escape(item.name_vi)}</strong><span>${money.format(item.price_vnd)}</span></a>`).join('');
      status(data.notice, data.mode === 'demo' && data.notice.includes('không khả dụng'));
      $('.studio-output').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (error) {
      showSample('Không thể hiển thị bản xem trước: ' + error.message + ' Ảnh mẫu hiện tại không phản ánh sản phẩm đã chọn.');
      $('#studio-status').classList.add('error');
    } finally {
      clearInterval(timer); $('#studio-progress').hidden = true;
      form.querySelectorAll('select,input').forEach(control => { control.disabled = false; });
      for (const category of categories) if (!(catalogue[category] || []).length) form.elements[category].disabled = true;
      busy = false; updateForm();
    }
  });
  loadCatalog();
})();
