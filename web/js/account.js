(() => {
  'use strict';
  const { request, current, setSession, money, escape } = window.CoguCommerce;
  const $ = selector => document.querySelector(selector);
  let mode = 'login';
  let editingAddress = null;
  let addresses = [];
  const aiSection = document.createElement('section');
  aiSection.id = 'shopping-preferences'; aiSection.className = 'commerce-card ai-preferences'; aiSection.hidden = true;
  aiSection.innerHTML = `<p class="kicker">COGU / FOR YOU</p><h2>Gu của bạn, gợi ý của COGU.</h2>
    <p>Lưu phong cách, màu thích và ngân sách. Gợi ý chỉ lấy sản phẩm còn hàng trong catalogue.</p>
    <form id="preferences-form" class="commerce-form"><label>Phong cách<select name="style"></select></label><fieldset><legend>Màu yêu thích · tối đa 5</legend><div id="preference-colors" class="preference-colors"></div></fieldset><label>Ngân sách tối đa (VND; 0 là không giới hạn)<input name="budget_vnd" type="number" min="0" max="50000000" step="1000" value="0"></label><button class="button button-green" type="submit">Lưu sở thích và xem gợi ý</button></form>
    <p id="recommendation-status" class="commerce-status" role="status" aria-live="polite"></p><div id="recommendation-list" class="recommendation-grid"></div>`;
  document.querySelector('#main').append(aiSection);
  document.querySelector('.account-nav').insertAdjacentHTML('beforeend', '<a href="#shopping-preferences">Gợi ý cho bạn</a>');
  function status(message, error = false) { const node = $('#page-status'); node.textContent = message; node.classList.toggle('error', error); }
  function setMode(next) {
    mode = next;
    $('#login-tab').setAttribute('aria-selected', String(mode === 'login'));
    $('#register-tab').setAttribute('aria-selected', String(mode === 'register'));
    $('#name-field').hidden = mode !== 'register';
    $('#name-field input').required = mode === 'register';
    $('#auth-password').autocomplete = mode === 'register' ? 'new-password' : 'current-password';
    $('#auth-password').minLength = mode === 'register' ? 10 : 1;
    $('#auth-submit').textContent = mode === 'register' ? 'Tạo tài khoản' : 'Đăng nhập';
  }
  async function loadAccount() {
    const session = await current();
    $('#auth-section').hidden = Boolean(session);
    $('#account-section').hidden = !session;
    $('#account-extras').hidden = !session;
    aiSection.hidden = !session;
    if (!session) { status('Đăng nhập hoặc tạo tài khoản để lưu giỏ hàng và xem đơn của bạn.'); return; }
    const target = new URLSearchParams(location.search).get('return');
    if (target && target.startsWith('/') && !target.startsWith('//') && !target.startsWith('/\\')) { location.replace(target); return; }
    $('#welcome').textContent = `Xin chào, ${session.customer.name}`;
    $('#profile-form').elements.name.value = session.customer.name;
    $('#profile-form').elements.phone.value = session.customer.phone || '';
    await Promise.all([loadAddresses(), loadWishlist(), loadOrders(), loadSupport(), loadReviews(), loadShoppingPreferences()]);
    status('');
  }
  async function loadAddresses() {
    addresses = (await request('/api/account/addresses')).addresses;
    $('#address-list').innerHTML = addresses.length ? addresses.map(address => `<div class="address-row"><div><strong>${escape(address.recipient)}</strong>${address.is_default ? '<span class="badge">Mặc định</span>' : ''}<p>${escape(address.phone)} · ${escape(address.line1)}, ${escape(address.ward)}, ${escape(address.district)}, ${escape(address.city)}</p>${address.note ? `<p>${escape(address.note)}</p>` : ''}</div><div class="commerce-actions"><button class="text-action" type="button" data-edit-address="${address.id}">Sửa</button><button class="text-action" type="button" data-delete-address="${address.id}">Xóa</button></div></div>`).join('') : '<p class="empty-state">Chưa có địa chỉ. Thêm một địa chỉ để đặt hàng.</p>';
  }
  async function loadWishlist() {
    const products = (await request('/api/account/wishlist')).products;
    $('#wishlist-list').innerHTML = products.length ? products.map(product => `<div class="wishlist-row"><img src="/${escape(product.image)}" alt=""><div><a href="/product?slug=${encodeURIComponent(product.slug)}"><strong>${escape(product.name_vi)}</strong></a><p>${money.format(product.price_vnd)}</p></div><button class="text-action" type="button" data-remove-wish="${product.id}">Bỏ lưu</button></div>`).join('') : '<p class="empty-state">Chưa có sản phẩm yêu thích. <a href="/shop">Khám phá cửa hàng →</a></p>';
  }
  async function loadOrders() {
    const orders = (await request('/api/account/orders')).orders;
    const paymentLabels = { pending_cod: 'COD chưa thu tiền', collected: 'Nhân viên ghi nhận đã thu COD', refunded: 'Nhân viên ghi nhận hoàn tiền' };
    $('#order-list').innerHTML = orders.length ? orders.map(order => `<div class="order-row"><div><a href="/order?ref=${encodeURIComponent(order.reference)}"><strong>${escape(order.reference)}</strong></a><p>${escape(order.created_at)} · ${order.items.length} món · ${money.format(order.total_vnd)}</p><span class="badge">${order.order_status === 'cancelled' ? 'Đã hủy · không thu COD' : escape(paymentLabels[order.payment_status] || order.payment_status)}</span></div><a class="text-link" href="/order?ref=${encodeURIComponent(order.reference)}">Chi tiết →</a></div>`).join('') : '<p class="empty-state">Chưa có đơn hàng nào. <a href="/shop">Chọn món đầu tiên →</a></p>';
  }
  async function loadSupport() {
    const requests = (await request('/api/account/support')).requests;
    $('#support-list').innerHTML = requests.length ? requests.map(item => `<div class="order-row"><div><strong>${escape(item.subject)}</strong><span class="badge">${escape(item.status)}</span><p>${escape(item.message)}</p>${item.response ? `<p><strong>COGU trả lời:</strong> ${escape(item.response)}</p>` : ''}<small>${escape(item.created_at)}</small></div></div>`).join('') : '<p class="empty-state">Chưa có yêu cầu hỗ trợ.</p>';
  }
  async function loadReviews() {
    const data = await request('/api/account/reviews');
    const reviews = data.reviews;
    $('#reviewable-list').innerHTML = data.reviewable_products.length
      ? `<h3>Sẵn sàng đánh giá</h3>${data.reviewable_products.map(item => `<div class="wishlist-row"><img src="/${escape(item.image)}" alt=""><div><a href="/product?slug=${encodeURIComponent(item.slug)}"><strong>${escape(item.name_vi)}</strong></a><p>Đơn đã hoàn tất · Đã mua hàng</p></div><a class="text-link" href="/product?slug=${encodeURIComponent(item.slug)}#reviews-section">Viết đánh giá →</a></div>`).join('')}`
      : '<p class="empty-state">Chưa có sản phẩm đủ điều kiện đánh giá.</p>';
    $('#my-review-list').innerHTML = reviews.length ? reviews.map(item => `<div class="order-row"><div><a href="/product?slug=${encodeURIComponent(item.slug)}"><strong>${escape(item.name_vi)}</strong></a><p>${'★'.repeat(item.rating)} · ${escape(item.comment)}</p><span class="badge">${{pending:'Chờ duyệt',approved:'Đã duyệt',rejected:'Không được duyệt'}[item.status] || escape(item.status)}</span></div></div>`).join('') : '<p class="empty-state">Chưa có đánh giá.</p>';
  }
  async function loadShoppingPreferences() {
    const data = await request('/api/ai/preferences');
    const form = $('#preferences-form');
    form.elements.style.innerHTML = Object.entries(data.styles).map(([key, label]) => `<option value="${escape(key)}">${escape(label)}</option>`).join('');
    form.elements.style.value = data.preferences.style;
    form.elements.budget_vnd.value = data.preferences.budget_vnd;
    $('#preference-colors').innerHTML = data.colors.map(color => `<label><input type="checkbox" name="color" value="${escape(color)}" ${data.preferences.colors.includes(color) ? 'checked' : ''}> ${escape(color)}</label>`).join('');
    await loadRecommendations();
  }
  async function loadRecommendations() {
    const statusNode = $('#recommendation-status');
    statusNode.textContent = 'Đang tìm sản phẩm còn hàng phù hợp…';
    $('#recommendation-list').setAttribute('aria-busy', 'true');
    try {
      const data = await request('/api/ai/recommendations');
      statusNode.textContent = data.label;
      $('#recommendation-list').innerHTML = data.recommendations.length ? data.recommendations.map(item => `<article class="recommendation-card"><a href="/product?slug=${encodeURIComponent(item.product.slug)}"><img src="/${escape(item.product.image)}" alt="" loading="lazy"><h3>${escape(item.product.name_vi)}</h3></a><strong>${money.format(item.product.price_vnd)}</strong><p>${escape(item.explanation)}</p></article>`).join('') : '<p class="empty-state">Không có sản phẩm còn hàng trong ngân sách này. Hãy tăng ngân sách hoặc chọn 0.</p>';
    } catch (error) { statusNode.textContent = error.message; statusNode.classList.add('error'); }
    finally { $('#recommendation-list').setAttribute('aria-busy', 'false'); }
  }
  $('#preferences-form').addEventListener('submit', async event => {
    event.preventDefault(); const form = event.currentTarget; const button = form.querySelector('button');
    const colors = [...form.querySelectorAll('input[name=color]:checked')].map(input => input.value);
    button.disabled = true; $('#recommendation-status').textContent = 'Đang lưu sở thích…';
    try {
      await request('/api/ai/preferences', 'PUT', { style: form.elements.style.value, colors, budget_vnd: Number(form.elements.budget_vnd.value) });
      await loadRecommendations();
    } catch (error) { $('#recommendation-status').textContent = error.message; $('#recommendation-status').classList.add('error'); }
    finally { button.disabled = false; }
  });
  function resetAddress() { editingAddress = null; $('#address-form').reset(); $('#address-form-title').textContent = 'Thêm địa chỉ'; $('#cancel-address').hidden = true; }
  $('#login-tab').addEventListener('click', () => setMode('login'));
  $('#register-tab').addEventListener('click', () => setMode('register'));
  $('#auth-form').addEventListener('submit', async event => {
    event.preventDefault();
    const button = $('#auth-submit'); button.disabled = true; status('Đang xác thực…');
    try {
      const form = new FormData(event.currentTarget);
      const body = { email: form.get('email'), password: form.get('password') };
      if (mode === 'register') body.name = form.get('name');
      setSession(await request(`/api/auth/${mode === 'register' ? 'register' : 'login'}`, 'POST', body));
      await loadAccount();
    } catch (error) { status(error.message, true); }
    finally { button.disabled = false; }
  });
  $('#logout').addEventListener('click', async () => { try { await request('/api/auth/logout', 'POST'); setSession(null); resetAddress(); await loadAccount(); } catch (error) { status(error.message, true); } });
  $('#profile-form').addEventListener('submit', async event => {
    event.preventDefault(); try { const form = new FormData(event.currentTarget); const data = await request('/api/account/profile', 'PUT', { name: form.get('name'), phone: form.get('phone') }); const session = await current(); session.customer = data.customer; $('#welcome').textContent = `Xin chào, ${data.customer.name}`; status('Đã lưu hồ sơ.'); } catch (error) { status(error.message, true); }
  });
  $('#address-form').addEventListener('submit', async event => {
    event.preventDefault(); const form = new FormData(event.currentTarget); const body = Object.fromEntries(form.entries()); body.is_default = form.has('is_default');
    try { await request(editingAddress ? `/api/account/addresses/${editingAddress}` : '/api/account/addresses', editingAddress ? 'PUT' : 'POST', body); resetAddress(); await loadAddresses(); status('Đã lưu địa chỉ.'); } catch (error) { status(error.message, true); }
  });
  $('#cancel-address').addEventListener('click', resetAddress);
  $('#address-list').addEventListener('click', async event => {
    const edit = event.target.closest('[data-edit-address]'); const remove = event.target.closest('[data-delete-address]');
    if (edit) { const address = addresses.find(item => item.id === Number(edit.dataset.editAddress)); if (!address) return; editingAddress = address.id; const form = $('#address-form'); for (const key of ['recipient', 'phone', 'line1', 'ward', 'district', 'city', 'note']) form.elements[key].value = address[key]; form.elements.is_default.checked = Boolean(address.is_default); $('#address-form-title').textContent = 'Sửa địa chỉ'; $('#cancel-address').hidden = false; form.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
    if (remove) { if (!confirm('Xóa địa chỉ này?')) return; try { await request(`/api/account/addresses/${remove.dataset.deleteAddress}`, 'DELETE'); await loadAddresses(); status('Đã xóa địa chỉ.'); } catch (error) { status(error.message, true); } }
  });
  $('#wishlist-list').addEventListener('click', async event => { const button = event.target.closest('[data-remove-wish]'); if (!button) return; try { await request(`/api/account/wishlist/${button.dataset.removeWish}`, 'DELETE'); await loadWishlist(); status('Đã bỏ sản phẩm khỏi danh sách yêu thích.'); } catch (error) { status(error.message, true); } });
  $('#support-form').addEventListener('submit', async event => {
    event.preventDefault(); const form = event.currentTarget; const fields = new FormData(form);
    try { await request('/api/account/support', 'POST', { subject: fields.get('subject'), message: fields.get('message') }); form.reset(); await loadSupport(); status('Đã gửi yêu cầu hỗ trợ.'); } catch (error) { status(error.message, true); }
  });
  loadAccount().catch(error => status(error.message, true));
})();
