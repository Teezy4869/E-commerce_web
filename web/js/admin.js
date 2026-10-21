(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const money = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 });
  const escape = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
  const categoryLabels = { shirt: 'Áo', trousers: 'Quần', shoes: 'Giày/dép' };
  const labels = { administrator: 'Quản trị viên', manager: 'Quản lý', sales: 'Bán hàng', warehouse: 'Kho', support: 'Chăm sóc khách',
    confirmed: 'Đã xác nhận', cancelled: 'Đã hủy', fulfilled: 'Hoàn tất', pending_cod: 'COD chờ thu', collected: 'Nhân viên ghi nhận đã thu', refunded: 'Nhân viên ghi nhận hoàn tiền',
    pending: 'Chờ xử lý', packing: 'Đang đóng gói', shipped: 'Đang giao', delivered: 'Đã giao', open: 'Mới', in_progress: 'Đang xử lý', resolved: 'Đã giải quyết', approved: 'Đã duyệt', rejected: 'Từ chối' };
  const title = { dashboard: ['COGU OPERATIONS', 'Tổng quan cửa hàng', 'Theo dõi đơn hàng, thanh toán COD và tồn kho theo dữ liệu hiện tại.'],
    products: ['CATALOGUE', 'Sản phẩm & tồn kho', 'Chỉnh sửa danh mục và từng biến thể màu / cỡ.'],
    orders: ['ORDER DESK', 'Đơn hàng khách', 'Quản lý trạng thái nội bộ của đơn, giao hàng và thu COD.'],
    promotions: ['CAMPAIGNS', 'Mã ưu đãi', 'Thay đổi tại đây áp dụng ngay cho báo giá giỏ hàng.'],
    reviews: ['COMMUNITY', 'Đánh giá đã mua', 'Duyệt bài viết từ khách có đơn hoàn tất.'],
    support: ['CUSTOMER CARE', 'Yêu cầu hỗ trợ', 'Phản hồi hiển thị trong tài khoản khách hàng.'],
    reports: ['PERFORMANCE', 'Báo cáo bán hàng & kho', 'Đơn đã đặt, thu COD do nhân viên ghi nhận và tồn kho.'],
    staff: ['ACCESS CONTROL', 'Nhân sự & phân quyền', 'Tạo tài khoản và quản lý quyền theo vai trò.'] };
  let auth = null;
  let view = 'dashboard';
  let products = [];
  let orders = [];
  let selectedProduct = null;
  let selectedVariant = null;
  let selectedOrder = null;
  let selectedPromotion = null;
  let promotions = [];
  const can = permission => Boolean(auth?.permissions.includes(permission));
  function status(message, error = false) { $('#admin-status').textContent = message; $('#admin-status').classList.toggle('error', error); }
  function loginStatus(message, error = false) { $('#login-status').textContent = message; $('#login-status').classList.toggle('error', error); }
  async function request(path, method = 'GET', body) {
    const headers = { Accept: 'application/json' };
    if (method !== 'GET') { headers['Content-Type'] = 'application/json'; if (auth?.csrf_token) headers['X-CSRF-Token'] = auth.csrf_token; }
    const response = await fetch(path, { method, credentials: 'same-origin', headers,
      body: method === 'GET' ? undefined : JSON.stringify(body || {}) });
    const data = await response.json();
    if (!response.ok) { const error = new Error(data.message || `Yêu cầu thất bại (${response.status})`); error.status = response.status; throw error; }
    return data;
  }
  function showApp() {
    $('#admin-login').hidden = Boolean(auth);
    $('#admin-app').hidden = !auth;
    if (!auth) return;
    $('#staff-identity').textContent = `${auth.staff.name} · ${labels[auth.staff.role]}`;
    document.querySelectorAll('[data-permission]').forEach(node => { node.hidden = !can(node.dataset.permission); });
    if (!can(title[view] ? ({dashboard:'dashboard',products:'products.read',orders:'orders.read',promotions:'promotions.read',reviews:'reviews.read',support:'support.read',reports:'reports',staff:'staff.read'}[view]) : 'dashboard')) {
      view = auth.staff.role === 'support' ? 'support' : ['dashboard','products','orders','promotions','reviews','support','reports','staff'].find(key => can(({dashboard:'dashboard',products:'products.read',orders:'orders.read',promotions:'promotions.read',reviews:'reviews.read',support:'support.read',reports:'reports',staff:'staff.read'})[key]));
    }
    showView(view);
  }
  function showView(next) {
    if (!title[next]) return;
    view = next;
    document.querySelectorAll('[data-panel]').forEach(node => { node.hidden = node.dataset.panel !== next; });
    document.querySelectorAll('#admin-nav button').forEach(node => node.classList.toggle('active', node.dataset.view === next));
    $('#view-kicker').textContent = title[next][0]; $('#view-title').textContent = title[next][1]; $('#view-description').textContent = title[next][2];
    $('#admin-sidebar').classList.remove('is-open'); $('#admin-menu').setAttribute('aria-expanded', 'false');
    status(''); loadView().catch(error => status(error.message, true));
  }
  async function loadView() {
    if (view === 'dashboard') return renderDashboard((await request('/api/admin/dashboard')).dashboard);
    if (view === 'products') { products = (await request('/api/admin/products')).products; return renderProducts(); }
    if (view === 'orders') { orders = (await request('/api/admin/orders')).orders; return renderOrders(); }
    if (view === 'promotions') { promotions = (await request('/api/admin/promotions')).promotions; return renderPromotions(); }
    if (view === 'reviews') return renderReviews((await request('/api/admin/reviews')).reviews);
    if (view === 'support') return renderSupport((await request('/api/admin/support')).requests);
    if (view === 'reports') return renderReports((await request('/api/admin/reports')).reports);
    if (view === 'staff') return renderStaff((await request('/api/admin/staff')).staff);
  }
  function metric(label, value, note) { return `<article class="metric"><span class="metric-label">${escape(label)}</span><strong>${escape(value)}</strong><span class="metric-note">${escape(note)}</span></article>`; }
  function renderDashboard(data) {
    $('#dashboard-metrics').innerHTML = [metric('Đơn hàng', data.orders_total || 0, `${data.orders_active || 0} đang xử lý`),
      metric('COD đang chờ thu', money.format(data.pending_cod_vnd || 0), `${data.pending_payment_count || 0} đơn chưa ghi nhận thu`),
      metric('COD đã ghi nhận thu', money.format(data.settled_revenue_vnd || 0), 'Do nhân viên cập nhật · không xác minh bên ngoài'),
      metric('Biến thể sắp hết', data.low_stock_variants || 0, `${data.sold_out_variants || 0} biến thể hết hàng`)].join('');
    $('#low-stock-list').innerHTML = data.low_stock.length ? data.low_stock.map(item => `<div class="mini-row"><div><strong>${escape(item.name_vi)}</strong><small>${escape(item.sku)} · ${escape(item.color)} / ${escape(item.size)}</small></div><span class="pill ${item.stock === 0 ? 'danger' : 'warn'}">${item.stock} còn</span></div>`).join('') : '<p class="empty">Chưa có biến thể tồn kho thấp.</p>';
    $('#recent-orders').innerHTML = data.recent_orders.length ? data.recent_orders.map(order => `<div class="mini-row"><div><strong>${escape(order.reference)}</strong><small>${escape(order.customer.name)} · ${money.format(order.total_vnd)}</small></div><span class="pill">${escape(labels[order.order_status] || order.order_status)}</span></div>`).join('') : '<p class="empty">Chưa có đơn hàng.</p>';
  }
  function renderProducts() {
    const query = $('#product-filter').value.trim().toLowerCase();
    const rows = products.filter(item => `${item.name_vi} ${item.slug} ${item.category} ${item.skus || ''}`.toLowerCase().includes(query));
    $('#product-rows').innerHTML = rows.length ? rows.map(item => `<tr><td><strong>${escape(item.name_vi)}</strong><small>${escape(item.slug)}</small></td><td>${escape(categoryLabels[item.category] || item.category)}</td><td>${money.format(item.price_vnd)}</td><td>${item.variant_count}</td><td><span class="pill ${item.stock === 0 ? 'danger' : item.stock <= 5 ? 'warn' : ''}">${item.stock}</span></td><td><button class="admin-text-button" data-product-id="${item.id}" type="button">Mở →</button></td></tr>`).join('') : '<tr><td colspan="6" class="empty">Không tìm thấy sản phẩm.</td></tr>';
  }
  async function editProduct(id) {
    selectedProduct = (await request(`/api/admin/products/${id}`)).product;
    selectedVariant = null;
    const form = $('#product-form');
    for (const key of ['slug','name_vi','description_vi','category','material','price_vnd','image']) form.elements[key].value = selectedProduct[key];
    form.elements.is_new.checked = Boolean(selectedProduct.is_new); form.elements.is_bestseller.checked = Boolean(selectedProduct.is_bestseller);
    $('#product-editor-title').textContent = `Chỉnh sửa · ${selectedProduct.name_vi}`;
    $('#product-editor').hidden = false; $('#variant-management').hidden = false;
    $('#delete-product').hidden = !can('products.write');
    form.querySelector('button[type=submit]').hidden = !can('products.write');
    form.querySelectorAll('input,select,textarea').forEach(node => { node.disabled = !can('products.write'); });
    $('#variant-form').hidden = !can('variants.write');
    renderVariants();
    $('#product-editor').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  function renderVariants() {
    $('#variant-rows').innerHTML = selectedProduct.variants.length ? selectedProduct.variants.map(item => `<tr><td>${escape(item.sku)}</td><td>${escape(item.color)}</td><td>${escape(item.size)}</td><td>${item.stock}</td><td>${can('variants.write') ? `<div class="action-group"><button class="admin-text-button" type="button" data-edit-variant="${item.id}">Sửa</button><button class="admin-text-button" type="button" data-delete-variant="${item.id}">Xóa</button></div><form class="inline-form" data-stock-form="${item.id}"><label class="sr-only" for="stock-${item.id}">Tồn kho mới</label><input class="inline-input" id="stock-${item.id}" name="stock" type="number" min="0" max="100000" value="${item.stock}" required><input class="inline-input" name="note" placeholder="Lý do" required minlength="5" style="width:140px"><button class="admin-outline" type="submit">Lưu kho</button></form>` : ''}</td></tr>`).join('') : '<tr><td colspan="5" class="empty">Chưa có biến thể. Thêm màu và cỡ để khách đặt hàng.</td></tr>';
  }
  function newProduct() {
    selectedProduct = null; selectedVariant = null;
    $('#product-form').reset(); $('#product-editor-title').textContent = 'Thêm sản phẩm mới';
    $('#product-editor').hidden = false; $('#variant-management').hidden = true; $('#delete-product').hidden = true;
    $('#product-editor').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  function renderOrders() {
    const query = $('#order-filter').value.trim().toLowerCase();
    const rows = orders.filter(order => `${order.reference} ${order.customer.email} ${order.customer.name}`.toLowerCase().includes(query));
    $('#order-count').textContent = `${orders.length} đơn`;
    $('#order-rows').innerHTML = rows.length ? rows.map(order => `<tr><td><strong>${escape(order.reference)}</strong><small>${escape(order.created_at)}</small></td><td>${escape(order.customer.name)}<small>${escape(order.customer.email)}</small></td><td>${money.format(order.total_vnd)}</td><td><span class="pill">${escape(labels[order.order_status] || order.order_status)}</span></td><td><span class="pill ${order.payment_status === 'pending_cod' ? 'warn' : ''}">${escape(labels[order.payment_status] || order.payment_status)}</span></td><td><span class="pill">${escape(labels[order.shipment_status] || order.shipment_status)}</span></td><td><button class="admin-text-button" type="button" data-order-ref="${escape(order.reference)}">Chi tiết →</button></td></tr>`).join('') : '<tr><td colspan="7" class="empty">Chưa có đơn hàng phù hợp.</td></tr>';
  }
  function orderForm(kind, heading, options) {
    return `<form data-order-action="${kind}" class="admin-form"><h3>${heading}</h3><div class="inline-form"><select name="status" class="inline-select">${options.map(([value,label]) => `<option value="${value}">${label}</option>`).join('')}</select><input name="note" placeholder="Ghi chú vận hành (ít nhất 8 ký tự)" required minlength="8" maxlength="240"><button class="admin-primary" type="submit">Cập nhật</button></div>${kind === 'shipment' ? '<label>Mã vận đơn nội bộ (nếu có)<input name="tracking_reference" maxlength="80"></label>' : ''}</form>`;
  }
  function renderOrderDetail() {
    const order = selectedOrder;
    if (!order) { $('#order-detail').hidden = true; return; }
    let forms = '';
    if (can('orders.write') && order.order_status === 'confirmed') {
      const options = [];
      if (['pending','packing'].includes(order.shipment_status) && order.payment_status === 'pending_cod') options.push(['cancelled','Hủy đơn & hoàn tồn kho']);
      if (order.shipment_status === 'delivered' && order.payment_status === 'collected') options.push(['fulfilled','Hoàn tất đơn']);
      if (options.length) forms += orderForm('status', 'Trạng thái đơn', options);
    }
    const next = {pending:['packing','Đang đóng gói'],packing:['shipped','Đang giao'],shipped:['delivered','Đã giao']};
    if (can('shipments.write') && order.order_status === 'confirmed' && next[order.shipment_status]) forms += orderForm('shipment', 'Giao hàng · nhân viên ghi nhận', [next[order.shipment_status]]);
    if (can('payments.write') && order.order_status === 'confirmed' && order.shipment_status === 'delivered' && order.payment_status === 'pending_cod') forms += orderForm('payment', 'Thu COD · nhân viên ghi nhận', [['collected','Đã thu COD']]);
    if (can('payments.write') && order.payment_status === 'collected') forms += orderForm('payment', 'Điều chỉnh khoản thu COD', [['refunded','Đã hoàn tiền']]);
    const address = order.address;
    $('#order-detail').innerHTML = `<div class="card-heading"><div><p class="eyebrow">ORDER DETAIL</p><h2>${escape(order.reference)}</h2></div><button class="admin-text-button" type="button" id="close-order-detail">Đóng ×</button></div><p class="admin-muted">${escape(order.customer.name)} · ${escape(order.customer.email)} · ${escape(order.created_at)}</p><div class="admin-order-items">${order.items.map(item => `<div><span>${escape(item.name_vi)} · ${escape(item.color)} / ${escape(item.size)} · ${escape(item.sku)} × ${item.quantity}</span><strong>${money.format(item.line_total_vnd)}</strong></div>`).join('')}</div><p><strong>Giao tới:</strong> ${escape(address.recipient)} · ${escape(address.phone)} · ${escape(address.line1)}, ${escape(address.ward)}, ${escape(address.district)}, ${escape(address.city)}</p><p><strong>Tổng COD:</strong> ${money.format(order.total_vnd)} · Ưu đãi ${escape(order.promotion_code || 'không')}</p><p><strong>Đơn:</strong> ${escape(labels[order.order_status] || order.order_status)} · <strong>Thu tiền:</strong> ${escape(labels[order.payment_status] || order.payment_status)} · <strong>Giao:</strong> ${escape(labels[order.shipment_status] || order.shipment_status)}</p><p class="admin-disclosure">Cập nhật thu COD và giao hàng là ghi nhận nội bộ của nhân viên. Không phải giao dịch được bên thứ ba xác minh.</p><div class="order-actions">${forms || '<p class="admin-muted">Không có chuyển trạng thái khả dụng cho vai trò hoặc trạng thái hiện tại.</p>'}</div><h3>Nhật ký xử lý</h3>${order.events.length ? order.events.map(event => `<div class="event-row">${escape(event.created_at)} · ${escape(event.staff_name)} · ${escape(event.event_type)}: ${escape(event.previous_value)} → ${escape(event.new_value)} · ${escape(event.note)}</div>`).join('') : '<p class="empty">Chưa có thay đổi vận hành.</p>'}`;
    $('#order-detail').hidden = false;
    $('#order-detail').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  function renderPromotions() {
    $('#promotion-list').innerHTML = promotions.length ? promotions.map(item => `<div class="promo-entry"><div class="entry-top"><div><h3>${escape(item.code)}</h3><small>${escape(item.description || '')}</small></div><span class="pill ${item.active ? '' : 'danger'}">${item.active ? 'Đang dùng' : 'Tạm dừng'}</span></div><p class="entry-text">${item.kind === 'percent' ? `${item.value}%` : item.kind === 'amount' ? money.format(item.value) : 'Miễn phí giao hàng'} · Đã dùng ${item.used_count}${item.usage_limit ? ` / ${item.usage_limit}` : ''} lượt · Đơn tối thiểu ${money.format(item.min_subtotal_vnd)}</p>${can('promotions.write') ? `<div class="entry-actions"><button type="button" class="admin-outline" data-edit-promo="${escape(item.code)}">Sửa</button><button type="button" class="admin-danger" data-delete-promo="${escape(item.code)}">Xóa</button></div>` : ''}</div>`).join('') : '<p class="empty">Chưa có mã ưu đãi.</p>';
  }
  function editPromotion(code) {
    selectedPromotion = promotions.find(item => item.code === code);
    if (!selectedPromotion) return;
    const form = $('#promotion-form');
    for (const key of ['code','kind','value','max_discount_vnd','min_subtotal_vnd','description']) form.elements[key].value = selectedPromotion[key];
    for (const key of ['starts_at','ends_at','usage_limit']) form.elements[key].value = selectedPromotion[key] ?? '';
    form.elements.active.checked = Boolean(selectedPromotion.active);
    form.elements.code.readOnly = true;
    $('#promotion-form-title').textContent = `Chỉnh sửa · ${code}`;
    form.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  function resetPromotion() { selectedPromotion = null; const form = $('#promotion-form'); form.reset(); form.elements.code.readOnly = false; $('#promotion-form-title').textContent = 'Tạo mã ưu đãi'; }
  function renderReviews(reviews) {
    $('#review-list').innerHTML = reviews.length ? reviews.map(item => `<article class="review-entry"><div class="entry-top"><div><h3>${escape(item.name_vi)} · ${'★'.repeat(item.rating)}</h3><small>${escape(item.customer_name)} · ${escape(item.email)} · ${escape(item.created_at)}</small></div><span class="pill ${item.status === 'pending' ? 'warn' : ''}">${escape(labels[item.status] || item.status)}</span></div><p class="entry-text">${escape(item.comment)}</p><p class="admin-muted">Đã mua: đơn #${item.order_id}. Chỉ công khai khi đã duyệt.</p>${can('reviews.write') ? `<div class="entry-actions"><button class="admin-outline" type="button" data-review-id="${item.id}" data-review-status="approved">Duyệt</button><button class="admin-danger" type="button" data-review-id="${item.id}" data-review-status="rejected">Từ chối</button></div>` : ''}</article>`).join('') : '<p class="empty">Chưa có đánh giá.</p>';
  }
  function renderSupport(requests) {
    $('#support-admin-list').innerHTML = requests.length ? requests.map(item => `<article class="support-entry"><div class="entry-top"><div><h3>#${item.id} · ${escape(item.subject)}</h3><small>${escape(item.customer_name)} · ${escape(item.email)} · ${escape(item.created_at)}</small></div><span class="pill ${item.status === 'open' ? 'warn' : ''}">${escape(labels[item.status] || item.status)}</span></div><p class="entry-text">${escape(item.message)}</p>${can('support.write') ? `<form class="support-response" data-support-id="${item.id}"><label class="sr-only" for="response-${item.id}">Phản hồi</label><textarea id="response-${item.id}" name="response" maxlength="2000" placeholder="Phản hồi cho khách hàng...">${escape(item.response)}</textarea><div class="inline-form"><select name="status" class="inline-select"><option value="open" ${item.status === 'open' ? 'selected' : ''}>Mới</option><option value="in_progress" ${item.status === 'in_progress' ? 'selected' : ''}>Đang xử lý</option><option value="resolved" ${item.status === 'resolved' ? 'selected' : ''}>Đã giải quyết</option></select><button class="admin-primary" type="submit">Lưu phản hồi</button></div></form>` : item.response ? `<p class="admin-disclosure">COGU trả lời: ${escape(item.response)}</p>` : ''}</article>`).join('') : '<p class="empty">Chưa có yêu cầu hỗ trợ.</p>';
  }
  function bars(items, label, value, formatter) {
    if (!items.length) return '<p class="empty">Chưa có dữ liệu.</p>';
    const max = Math.max(...items.map(value), 1);
    return items.map(item => `<div class="bar-row"><span>${escape(label(item))}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.max(2, value(item) / max * 100)}%"></div></div><strong>${escape(formatter(value(item)))}</strong></div>`).join('');
  }
  function renderReports(data) {
    $('#sales-report').innerHTML = bars(data.sales_by_day, item => item.day, item => item.order_count, value => `${value} đơn`) + `<div class="table-wrap"><table><thead><tr><th>Ngày</th><th>Đơn</th><th>Đã đặt</th><th>COD ghi nhận đã thu</th></tr></thead><tbody>${data.sales_by_day.map(item => `<tr><td>${escape(item.day)}</td><td>${item.order_count}</td><td>${money.format(item.placed_value_vnd || 0)}</td><td>${money.format(item.settled_revenue_vnd || 0)}</td></tr>`).join('')}</tbody></table></div>`;
    $('#top-products').innerHTML = bars(data.top_products, item => item.name_vi, item => item.units, value => `${value} món`) + `<div class="table-wrap"><table><thead><tr><th>Sản phẩm</th><th>Số món</th><th>Giá trị đã đặt</th></tr></thead><tbody>${data.top_products.map(item => `<tr><td>${escape(item.name_vi)}</td><td>${item.units}</td><td>${money.format(item.placed_value_vnd || 0)}</td></tr>`).join('')}</tbody></table></div>`;
    $('#inventory-report').innerHTML = `<div class="table-wrap"><table><thead><tr><th>Danh mục</th><th>Sản phẩm</th><th>Biến thể</th><th>Số món trong kho</th><th>Giá trị theo giá bán</th></tr></thead><tbody>${data.inventory_by_category.map(item => `<tr><td>${escape(categoryLabels[item.category] || item.category)}</td><td>${item.products}</td><td>${item.variants}</td><td>${item.units}</td><td>${money.format(item.inventory_value_vnd)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function renderStaff(staff) {
    $('#staff-list').innerHTML = staff.map(item => `<div class="mini-row"><div><strong>${escape(item.name)}</strong><small>${escape(item.email)} · ${escape(labels[item.role])}</small></div><form class="inline-form" data-staff-id="${item.id}"><select name="role" class="inline-select">${['administrator','manager','sales','warehouse','support'].map(role => `<option value="${role}" ${item.role === role ? 'selected' : ''}>${escape(labels[role])}</option>`).join('')}</select><label class="check-label"><input name="active" type="checkbox" ${item.active ? 'checked' : ''}> Bật</label><button class="admin-outline" type="submit">Lưu</button></form></div>`).join('') || '<p class="empty">Chưa có nhân viên.</p>';
  }

  $('#staff-login-form').addEventListener('submit', async event => { event.preventDefault(); const button = event.currentTarget.querySelector('button'); button.disabled = true; loginStatus('Đang xác thực…'); try { const form = new FormData(event.currentTarget); auth = await request('/api/admin/login', 'POST', { email: form.get('email'), password: form.get('password') }); loginStatus(''); showApp(); } catch (error) { loginStatus(error.message, true); } finally { button.disabled = false; } });
  $('#staff-logout').addEventListener('click', async () => { try { await request('/api/admin/logout', 'POST'); auth = null; showApp(); } catch (error) { status(error.message, true); } });
  $('#admin-menu').addEventListener('click', () => { const open = $('#admin-sidebar').classList.toggle('is-open'); $('#admin-menu').setAttribute('aria-expanded', String(open)); });
  $('#admin-nav').addEventListener('click', event => { const button = event.target.closest('[data-view]'); if (button && !button.hidden) showView(button.dataset.view); });
  $('#refresh-view').addEventListener('click', () => { status('Đang làm mới…'); loadView().then(() => status('Đã cập nhật dữ liệu.')).catch(error => status(error.message, true)); });
  document.addEventListener('click', event => { const button = event.target.closest('[data-jump]'); if (button) showView(button.dataset.jump); });
  $('#product-filter').addEventListener('input', renderProducts);
  $('#new-product').addEventListener('click', newProduct);
  $('#close-product-editor').addEventListener('click', () => { $('#product-editor').hidden = true; selectedProduct = null; });
  $('#product-rows').addEventListener('click', event => { const button = event.target.closest('[data-product-id]'); if (button) editProduct(Number(button.dataset.productId)).catch(error => status(error.message, true)); });
  $('#product-form').addEventListener('submit', async event => { event.preventDefault(); const form = new FormData(event.currentTarget); const body = Object.fromEntries(form.entries()); body.price_vnd = Number(body.price_vnd); body.is_new = form.has('is_new'); body.is_bestseller = form.has('is_bestseller'); try { const path = selectedProduct ? `/api/admin/products/${selectedProduct.id}` : '/api/admin/products'; const data = await request(path, selectedProduct ? 'PUT' : 'POST', body); products = (await request('/api/admin/products')).products; renderProducts(); await editProduct(data.product.id); status('Đã lưu sản phẩm.'); } catch (error) { status(error.message, true); } });
  $('#delete-product').addEventListener('click', async () => { if (!selectedProduct || !confirm(`Xóa ${selectedProduct.name_vi}? Giỏ hàng và yêu thích liên quan sẽ bị cập nhật.`)) return; try { await request(`/api/admin/products/${selectedProduct.id}`, 'DELETE'); $('#product-editor').hidden = true; selectedProduct = null; products = (await request('/api/admin/products')).products; renderProducts(); status('Đã xóa sản phẩm.'); } catch (error) { status(error.message, true); } });
  $('#variant-rows').addEventListener('click', async event => { const edit = event.target.closest('[data-edit-variant]'); const remove = event.target.closest('[data-delete-variant]'); if (edit) { selectedVariant = selectedProduct.variants.find(item => item.id === Number(edit.dataset.editVariant)); const form = $('#variant-form'); for (const key of ['sku','color','size','stock']) form.elements[key].value = selectedVariant[key]; $('#variant-form-title').textContent = `Sửa · ${selectedVariant.sku}`; form.scrollIntoView({ behavior: 'smooth', block: 'center' }); } if (remove) { if (!confirm('Xóa biến thể này? Mục trong giỏ hàng liên quan sẽ bị gỡ.')) return; try { await request(`/api/admin/variants/${remove.dataset.deleteVariant}`, 'DELETE'); await editProduct(selectedProduct.id); status('Đã xóa biến thể.'); } catch (error) { status(error.message, true); } } });
  $('#variant-rows').addEventListener('submit', async event => { const form = event.target.closest('[data-stock-form]'); if (!form) return; event.preventDefault(); const fields = new FormData(form); try { await request(`/api/admin/variants/${form.dataset.stockForm}/stock`, 'PUT', { stock: Number(fields.get('stock')), note: fields.get('note') }); await editProduct(selectedProduct.id); status('Đã cập nhật tồn kho.'); } catch (error) { status(error.message, true); } });
  $('#variant-form').addEventListener('submit', async event => { event.preventDefault(); const fields = new FormData(event.currentTarget); const body = Object.fromEntries(fields.entries()); body.stock = Number(body.stock); try { await request(selectedVariant ? `/api/admin/variants/${selectedVariant.id}` : `/api/admin/products/${selectedProduct.id}/variants`, selectedVariant ? 'PUT' : 'POST', body); await editProduct(selectedProduct.id); $('#variant-form').reset(); selectedVariant = null; $('#variant-form-title').textContent = 'Thêm biến thể'; status('Đã lưu biến thể.'); } catch (error) { status(error.message, true); } });
  $('#cancel-variant').addEventListener('click', () => { selectedVariant = null; $('#variant-form').reset(); $('#variant-form-title').textContent = 'Thêm biến thể'; });
  $('#order-filter').addEventListener('input', renderOrders);
  $('#order-rows').addEventListener('click', event => { const button = event.target.closest('[data-order-ref]'); if (!button) return; selectedOrder = orders.find(order => order.reference === button.dataset.orderRef); renderOrderDetail(); });
  $('#order-detail').addEventListener('click', event => { if (event.target.closest('#close-order-detail')) { $('#order-detail').hidden = true; selectedOrder = null; } });
  $('#order-detail').addEventListener('submit', async event => { const form = event.target.closest('[data-order-action]'); if (!form) return; event.preventDefault(); const fields = new FormData(form); const kind = form.dataset.orderAction; const body = { status: fields.get('status'), note: fields.get('note') }; if (kind === 'shipment') body.tracking_reference = fields.get('tracking_reference'); try { const result = await request(`/api/admin/orders/${selectedOrder.reference}/${kind}`, 'PUT', body); selectedOrder = result.order; orders = (await request('/api/admin/orders')).orders; renderOrders(); renderOrderDetail(); status('Đã ghi nhận thay đổi nội bộ.'); } catch (error) { status(error.message, true); } });
  $('#promotion-list').addEventListener('click', async event => { const edit = event.target.closest('[data-edit-promo]'); const remove = event.target.closest('[data-delete-promo]'); if (edit) editPromotion(edit.dataset.editPromo); if (remove) { if (!confirm(`Xóa mã ${remove.dataset.deletePromo}?`)) return; try { await request(`/api/admin/promotions/${remove.dataset.deletePromo}`, 'DELETE'); promotions = (await request('/api/admin/promotions')).promotions; renderPromotions(); resetPromotion(); status('Đã xóa mã ưu đãi.'); } catch (error) { status(error.message, true); } } });
  $('#promotion-form').addEventListener('submit', async event => { event.preventDefault(); const fields = new FormData(event.currentTarget); const body = Object.fromEntries(fields.entries()); for (const key of ['value','max_discount_vnd','min_subtotal_vnd']) body[key] = Number(body[key]); body.usage_limit = body.usage_limit ? Number(body.usage_limit) : null; body.active = fields.has('active'); try { await request(selectedPromotion ? `/api/admin/promotions/${selectedPromotion.code}` : '/api/admin/promotions', selectedPromotion ? 'PUT' : 'POST', body); promotions = (await request('/api/admin/promotions')).promotions; renderPromotions(); resetPromotion(); status('Đã lưu mã ưu đãi.'); } catch (error) { status(error.message, true); } });
  $('#reset-promotion').addEventListener('click', resetPromotion);
  $('#review-list').addEventListener('click', async event => { const button = event.target.closest('[data-review-id]'); if (!button) return; try { await request(`/api/admin/reviews/${button.dataset.reviewId}`, 'PUT', { status: button.dataset.reviewStatus }); renderReviews((await request('/api/admin/reviews')).reviews); status('Đã cập nhật đánh giá.'); } catch (error) { status(error.message, true); } });
  $('#support-admin-list').addEventListener('submit', async event => { const form = event.target.closest('[data-support-id]'); if (!form) return; event.preventDefault(); const fields = new FormData(form); try { await request(`/api/admin/support/${form.dataset.supportId}`, 'PUT', { status: fields.get('status'), response: fields.get('response') }); renderSupport((await request('/api/admin/support')).requests); status('Đã lưu phản hồi hỗ trợ.'); } catch (error) { status(error.message, true); } });
  $('#staff-form').addEventListener('submit', async event => { event.preventDefault(); const element = event.currentTarget; const form = new FormData(element); try { await request('/api/admin/staff', 'POST', Object.fromEntries(form.entries())); element.reset(); renderStaff((await request('/api/admin/staff')).staff); status('Đã tạo tài khoản nhân viên.'); } catch (error) { status(error.message, true); } });
  $('#staff-list').addEventListener('submit', async event => { const form = event.target.closest('[data-staff-id]'); if (!form) return; event.preventDefault(); const fields = new FormData(form); try { await request(`/api/admin/staff/${form.dataset.staffId}`, 'PUT', { role: fields.get('role'), active: fields.has('active') }); renderStaff((await request('/api/admin/staff')).staff); status('Đã cập nhật quyền nhân viên.'); } catch (error) { status(error.message, true); } });
  request('/api/admin/session').then(value => { auth = value; showApp(); }).catch(error => { if (error.status !== 401) loginStatus(error.message, true); showApp(); });
})();
