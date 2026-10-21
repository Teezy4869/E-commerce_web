(() => {
  'use strict';
  const { request, current, requireAccount, money, escape } = window.CoguCommerce;
  const $ = selector => document.querySelector(selector);
  async function load() {
    if (!await current()) { requireAccount(); return; }
    const ref = new URLSearchParams(location.search).get('ref');
    if (!/^COGU-\d{8}-[A-F0-9]{12}$/.test(ref || '')) throw new Error('Mã đơn hàng không hợp lệ.');
    const { order } = await request(`/api/account/orders/${encodeURIComponent(ref)}`);
    $('#order-reference').textContent = `Đơn ${order.reference}`;
    $('#order-date').textContent = `Đặt lúc ${order.created_at}`;
    $('#order-items').innerHTML = order.items.map(item => `<div class="order-item"><img src="/${escape(item.image)}" alt=""><div><h3>${escape(item.name_vi)}</h3><span>${escape(item.color)} · Cỡ ${escape(item.size)} · SKU ${escape(item.sku)} · SL ${item.quantity}</span></div><strong>${money.format(item.line_total_vnd)}</strong></div>`).join('');
    const address = order.address;
    $('#order-address').innerHTML = `<h3>Giao đến</h3><p>${escape(address.recipient)} · ${escape(address.phone)}<br>${escape(address.line1)}, ${escape(address.ward)}, ${escape(address.district)}, ${escape(address.city)}</p>`;
    const states = { confirmed: 'Đã xác nhận', cancelled: 'Đã hủy', fulfilled: 'Hoàn tất', pending_cod: 'COD: chờ thu tiền', collected: 'Nhân viên ghi nhận đã thu COD', failed: 'Thất bại', refunded: 'Nhân viên ghi nhận hoàn tiền', pending: 'Chờ xử lý', packing: 'Nhân viên ghi nhận đang đóng gói', shipped: 'Nhân viên ghi nhận đang giao', delivered: 'Nhân viên ghi nhận đã giao', cancelled_shipment: 'Đã hủy' };
    $('#order-states').innerHTML = [['Đơn hàng', order.order_status], ['Thanh toán', order.payment_status], ['Vận chuyển', order.shipment_status]].map(([label, value]) => `<div>${label}<strong>${escape(order.order_status === 'cancelled' && value === 'pending_cod' ? 'Không thu COD vì đơn đã hủy' : states[value] || value)}</strong></div>`).join('');
    $('#order-totals').innerHTML = `<div><span>Tạm tính</span><strong>${money.format(order.subtotal_vnd)}</strong></div><div><span>Giảm giá</span><strong>−${money.format(order.discount_vnd)}</strong></div><div><span>Phí giao hàng</span><strong>${money.format(order.delivery_fee_vnd)}</strong></div><div class="grand"><span>Tổng COD</span><span>${money.format(order.total_vnd)}</span></div>`;
    $('#order-disclosure').textContent = order.order_status === 'cancelled'
      ? 'Đơn đã hủy trong hệ thống demo; không có khoản COD nào được thu.'
      : order.payment_status === 'collected' || order.shipment_status === 'delivered'
      ? 'Trạng thái thu COD và giao hàng do nhân viên COGU ghi nhận trong bản demo; không có xác minh từ đơn vị thanh toán hoặc vận chuyển bên ngoài.'
      : 'Đơn COD chưa thu tiền trực tuyến. Trạng thái giao hàng là dữ liệu vận hành của bản demo.';
    $('#order-content').hidden = false;
    $('#order-status').textContent = order.order_status === 'cancelled' ? 'Đơn đã hủy. Mã đơn vẫn được lưu trong lịch sử của bạn.' : 'Đặt hàng thành công. Mã đơn đã được lưu trong lịch sử của bạn.';
  }
  load().catch(error => { $('#order-status').textContent = error.message; $('#order-status').classList.add('error'); });
})();
