(() => {
  'use strict';
  const { request, current, requireAccount, money, escape } = window.CoguCommerce;
  const $ = selector => document.querySelector(selector);
  let promo = '';
  let cart = null;
  let checkoutKey = null;
  function status(message, error = false) { $('#cart-status').textContent = message; $('#cart-status').classList.toggle('error', error); }
  async function load() {
    if (!await current()) { requireAccount(); return; }
    const [cartData, addressData, promotionData] = await Promise.all([request(`/api/cart?promotion_code=${encodeURIComponent(promo)}`), request('/api/account/addresses'), request('/api/promotions')]);
    cart = cartData.cart;
    $('#available-promotions').textContent = promotionData.promotions.length ? `Mã đang áp dụng: ${promotionData.promotions.map(item => item.code).join(', ')}.` : 'Hiện chưa có mã ưu đãi đang áp dụng.';
    $('#cart-content').hidden = false;
    $('#cart-items').innerHTML = cart.items.length ? cart.items.map(item => `<div class="cart-item"><a href="/product?slug=${encodeURIComponent(item.slug)}"><img src="/${escape(item.image)}" alt="${escape(item.name_vi)}"></a><div><h3><a href="/product?slug=${encodeURIComponent(item.slug)}">${escape(item.name_vi)}</a></h3><p>${escape(item.color)} · Cỡ ${escape(item.size)} · SKU ${escape(item.sku)}</p><strong>${money.format(item.price_vnd)}</strong><div class="cart-item-controls"><label class="sr-only" for="qty-${item.variant_id}">Số lượng ${escape(item.name_vi)}</label><input class="cart-quantity" id="qty-${item.variant_id}" type="number" min="1" max="10" value="${item.quantity}" data-quantity="${item.variant_id}"><button class="text-action" type="button" data-remove="${item.variant_id}">Xóa</button></div>${!item.available ? '<p class="commerce-status error">Số lượng vượt tồn kho hiện tại.</p>' : ''}</div><strong>${money.format(item.line_total_vnd)}</strong></div>`).join('') : '<p class="empty-state">Giỏ hàng đang trống. <a href="/shop">Khám phá cửa hàng →</a></p>';
    $('#cart-totals').innerHTML = `<div><span>Tạm tính</span><strong>${money.format(cart.subtotal_vnd)}</strong></div><div><span>Ưu đãi ${escape(cart.promotion_code)}</span><strong>−${money.format(cart.discount_vnd)}</strong></div><div><span>Phí giao hàng</span><strong>${money.format(cart.delivery_fee_vnd)}</strong></div><div class="grand"><span>Tổng thanh toán COD</span><span>${money.format(cart.total_vnd)}</span></div>`;
    const select = $('#checkout-address'); const previous = select.value;
    select.innerHTML = '<option value="">Chọn địa chỉ giao hàng</option>' + addressData.addresses.map(address => `<option value="${address.id}">${escape(address.recipient)} — ${escape(address.line1)}, ${escape(address.city)}</option>`).join('');
    select.value = addressData.addresses.some(address => String(address.id) === previous) ? previous : String(addressData.addresses.find(address => address.is_default)?.id || '');
    $('#checkout-button').disabled = !cart.can_checkout || !addressData.addresses.length;
    status(cart.items.length ? (cart.can_checkout ? '' : 'Kiểm tra số lượng hàng trước khi đặt đơn.') : 'Giỏ hàng đang trống.');
  }
  $('#cart-items').addEventListener('change', async event => { const input = event.target.closest('[data-quantity]'); if (!input) return; try { await request('/api/cart', 'PUT', { variant_id: Number(input.dataset.quantity), quantity: Number(input.value) }); checkoutKey = null; await load(); } catch (error) { await load(); status(error.message, true); } });
  $('#cart-items').addEventListener('click', async event => { const button = event.target.closest('[data-remove]'); if (!button) return; try { await request(`/api/cart/${button.dataset.remove}`, 'DELETE'); checkoutKey = null; await load(); } catch (error) { status(error.message, true); } });
  $('#promo-form').addEventListener('submit', async event => {
    event.preventDefault();
    const previous = promo;
    promo = $('#promo-code').value.trim().toUpperCase();
    try {
      await load();
      checkoutKey = null;
      status(promo ? 'Đã áp dụng mã ưu đãi.' : 'Đã bỏ mã ưu đãi.');
    } catch (error) {
      promo = previous;
      $('#promo-code').value = previous;
      status(error.message, true);
    }
  });
  $('#checkout-address').addEventListener('change', () => { checkoutKey = null; });
  $('#checkout-form').addEventListener('submit', async event => { event.preventDefault(); const button = $('#checkout-button'); button.disabled = true; status('Đang xác nhận đơn hàng…'); try { checkoutKey ||= crypto.randomUUID(); const data = await request('/api/checkout', 'POST', { address_id: Number($('#checkout-address').value), payment_method: 'cod', promotion_code: promo, idempotency_key: checkoutKey }); location.assign(`/order?ref=${encodeURIComponent(data.order.reference)}`); } catch (error) { status(error.message, true); button.disabled = false; } });
  load().catch(error => status(error.message, true));
})();
