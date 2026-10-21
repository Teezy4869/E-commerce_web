(() => {
  'use strict';
  const esc = window.CoguCatalog?.escape || (value => String(value));
  const money = window.CoguCatalog?.money || new Intl.NumberFormat('vi-VN');
  let csrf = '';
  async function sessionToken() {
    try {
      const response = await fetch('/api/auth/me', { credentials: 'same-origin' });
      if (response.ok) csrf = (await response.json()).csrf_token || '';
      else csrf = '';
    } catch { csrf = ''; }
  }
  async function post(path, body) {
    await sessionToken();
    const headers = { 'Content-Type': 'application/json' };
    if (csrf) headers['X-CSRF-Token'] = csrf;
    const response = await fetch(path, { method: 'POST', credentials: 'same-origin', headers, body: JSON.stringify(body) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Không thể kết nối trợ lý.');
    return data;
  }

  const widget = document.createElement('div');
  widget.className = 'cogu-chat';
  widget.innerHTML = `<button type="button" class="cogu-chat-toggle" aria-expanded="false" aria-controls="cogu-chat-panel">Hỏi COGU <span aria-hidden="true">✦</span></button>
    <section id="cogu-chat-panel" class="cogu-chat-panel" aria-label="Trợ lý mua sắm COGU" hidden>
      <div class="cogu-chat-head"><div><strong>Trợ lý COGU</strong><small>Thông tin từ catalogue và tài khoản của bạn</small></div><button type="button" class="cogu-chat-close" aria-label="Đóng trợ lý">×</button></div>
      <div class="cogu-chat-messages" id="cogu-chat-messages" role="log" aria-live="polite"><p class="cogu-chat-message">Xin chào! Hãy hỏi về sản phẩm, chất liệu, cỡ, COD hoặc đơn hàng của bạn.</p></div>
      <form class="cogu-chat-form"><label class="sr-only" for="cogu-chat-input">Câu hỏi của bạn</label><input id="cogu-chat-input" maxlength="400" required placeholder="Ví dụ: áo cotton còn màu nào?"><button type="submit">Gửi</button></form>
      <p class="cogu-ai-note">Dữ liệu đơn hàng chỉ được dùng khi bạn đăng nhập. Khi cấu hình LLM, dữ liệu liên quan có thể được gửi tới nhà cung cấp AI do chủ cửa hàng cấu hình.</p>
    </section>`;
  document.body.append(widget);
  const comingSoon = document.querySelector('.ai-section .coming-soon');
  if (comingSoon) {
    comingSoon.innerHTML = `<span>COGU / TRỢ LÝ MUA SẮM</span><div><p>Chat về sản phẩm và đơn hàng của bạn</p><p>So sánh 2–3 sản phẩm trong cửa hàng</p><p>Gợi ý theo sở thích cá nhân</p><p>Phối đồ trong AI Studio</p></div><div class="ai-phase7-links"><button type="button" class="button button-green" id="open-ai-chat">Hỏi COGU ngay</button><a href="/shop">So sánh sản phẩm</a><a href="/account#shopping-preferences">Xem gợi ý cho bạn</a><a href="/studio">Vào AI Studio</a></div>`;
    const subtitle = document.querySelector('.ai-section .section-subtitle');
    if (subtitle) subtitle.textContent = 'Tìm kiếm đa phương thức và ba trải nghiệm mua sắm thông minh dùng dữ liệu COGU hiện có.';
    comingSoon.querySelector('#open-ai-chat').addEventListener('click', () => setOpen(true));
  }
  const toggle = widget.querySelector('.cogu-chat-toggle');
  const panel = widget.querySelector('.cogu-chat-panel');
  const messages = widget.querySelector('#cogu-chat-messages');
  function setOpen(open) { panel.hidden = !open; toggle.setAttribute('aria-expanded', String(open)); if (open) widget.querySelector('input').focus(); }
  toggle.addEventListener('click', () => setOpen(panel.hidden));
  widget.querySelector('.cogu-chat-close').addEventListener('click', () => setOpen(false));
  widget.querySelector('form').addEventListener('submit', async event => {
    event.preventDefault();
    const input = widget.querySelector('input'); const question = input.value.trim(); if (!question) return;
    const button = widget.querySelector('form button'); button.disabled = true; input.disabled = true;
    const user = document.createElement('p'); user.className = 'cogu-chat-message is-user'; user.textContent = question; messages.append(user);
    const reply = document.createElement('p'); reply.className = 'cogu-chat-message'; reply.setAttribute('role', 'status'); reply.textContent = 'Đang tìm trong dữ liệu COGU…'; messages.append(reply);
    messages.scrollTop = messages.scrollHeight;
    try {
      const data = await post('/api/ai/chat', { message: question });
      reply.textContent = `${data.label}\n${data.answer}`; input.value = '';
    } catch (error) { reply.textContent = error.message; reply.classList.add('is-error'); }
    finally { button.disabled = false; input.disabled = false; input.focus(); messages.scrollTop = messages.scrollHeight; }
  });

  const grid = document.querySelector('#shop-grid');
  if (!grid) return;
  const selected = new Map();
  const tray = document.createElement('section');
  tray.className = 'compare-tray'; tray.setAttribute('aria-label', 'So sánh sản phẩm');
  tray.innerHTML = `<div><strong>So sánh sản phẩm</strong><span id="compare-count" aria-live="polite">Chọn 2–3 sản phẩm trong cửa hàng</span></div><button type="button" class="button button-green" id="compare-go" disabled>So sánh ngay</button>`;
  grid.parentElement.insertBefore(tray, grid);
  const result = document.createElement('section');
  result.id = 'compare-result'; result.className = 'compare-result'; result.hidden = true;
  grid.parentElement.insertBefore(result, grid);
  function updateSelection() {
    tray.querySelector('#compare-count').textContent = selected.size ? `${selected.size}/3 đã chọn: ${[...selected.values()].join(', ')}` : 'Chọn 2–3 sản phẩm trong cửa hàng';
    tray.querySelector('#compare-go').disabled = selected.size < 2;
    grid.querySelectorAll('[data-compare-id]').forEach(button => {
      const active = selected.has(Number(button.dataset.compareId));
      button.setAttribute('aria-pressed', String(active)); button.textContent = active ? '✓ Đã chọn so sánh' : '+ So sánh';
    });
  }
  tray.querySelector('#compare-count').addEventListener('cogu:refresh-selection', updateSelection);
  grid.addEventListener('click', event => {
    const button = event.target.closest('[data-compare-id]'); if (!button) return;
    const id = Number(button.dataset.compareId);
    if (selected.has(id)) selected.delete(id);
    else if (selected.size < 3) selected.set(id, button.dataset.compareName);
    else { tray.querySelector('#compare-count').textContent = 'Chỉ chọn tối đa 3 sản phẩm. Bỏ chọn một sản phẩm trước.'; return; }
    updateSelection();
  });
  tray.querySelector('#compare-go').addEventListener('click', async event => {
    const button = event.currentTarget; button.disabled = true; button.textContent = 'Đang so sánh…';
    result.hidden = false; result.innerHTML = '<p role="status">Đang lấy giá và tồn kho mới nhất…</p>';
    try {
      const data = await post('/api/ai/compare', { product_ids: [...selected.keys()] });
      const rows = [
        ['Giá', p => money.format(p.price_vnd)], ['Chất liệu', p => esc(p.material)],
        ['Cỡ', p => esc(p.sizes.join(', '))], ['Màu', p => esc(p.colors.join(', '))],
        ['Tồn kho', p => p.stock > 0 ? `${p.stock} trên các biến thể` : 'Hết hàng'],
        ['Màu/cỡ còn hàng', p => p.available_variants.length ? p.available_variants.map(v => `${esc(v.color)} / ${esc(v.size)} (${v.stock})`).join('<br>') : 'Không có biến thể còn hàng']
      ];
      result.innerHTML = `<div class="compare-result-head"><div><p class="kicker">COGU / COMPARE</p><h2>Đặt cạnh nhau, chọn đúng gu.</h2></div><button type="button" class="text-action" id="compare-close">Đóng ×</button></div>
        <div class="compare-scroll"><table><caption class="sr-only">So sánh sản phẩm COGU</caption><thead><tr><th scope="col">Tiêu chí</th>${data.products.map(p => `<th scope="col"><a href="/product?slug=${encodeURIComponent(p.slug)}">${esc(p.name_vi)}</a></th>`).join('')}</tr></thead><tbody>${rows.map(([name, value]) => `<tr><th scope="row">${name}</th>${data.products.map(p => `<td>${value(p)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
        <div class="compare-analysis"><span class="cogu-mode">${esc(data.label)}</span><h3>Điểm đáng cân nhắc</h3>${data.analysis.length ? `<ul>${data.analysis.map(item => `<li><strong>${item.kind === 'advantage' ? 'Ưu điểm' : item.kind === 'consideration' ? 'Cân nhắc' : 'Đặc điểm'}:</strong> ${esc(item.text)}</li>`).join('')}</ul>` : '<p>Chưa có điểm so sánh phù hợp.</p>'}<p class="cogu-ai-note">Tồn kho tổng có thể thay đổi. Mở sản phẩm để kiểm tra màu và cỡ cụ thể.</p></div>`;
      result.querySelector('#compare-close').addEventListener('click', () => { result.hidden = true; });
      result.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) { result.textContent = error.message; }
    finally { button.disabled = selected.size < 2; button.textContent = 'So sánh ngay'; }
  });
})();
