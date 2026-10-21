(() => {
  'use strict';
  const { json, card, money, names, imageUrl } = window.CoguCatalog;
  const $ = selector => document.querySelector(selector);
  const slug = new URLSearchParams(location.search).get('slug');
  let product;
  let color = '';
  let size = '';
  let stockRequest = 0;
  let favorite = false;

  function showImage(path, label) {
    $('#gallery-main').src = imageUrl(path);
    $('#gallery-main').alt = `${product.name_vi} – ${label}`;
    document.querySelectorAll('#gallery-thumbs button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.image === path)));
  }
  async function showStock() {
    const id = ++stockRequest;
    const panel = $('#stock-panel');
    if (!color || !size) { panel.textContent = 'Chọn màu và kích cỡ để xem tồn kho.'; return; }
    panel.textContent = 'Đang kiểm tra tồn kho…';
    try {
      const data = await json(`/api/catalog/stock?${new URLSearchParams({ slug, color, size })}`);
      if (id !== stockRequest) return;
      panel.classList.toggle('sold-out', data.variant.stock === 0);
      document.querySelector('#add-to-cart').disabled = data.variant.stock === 0;
      panel.textContent = data.variant.stock > 0
        ? `Còn ${data.variant.stock} sản phẩm · SKU ${data.variant.sku}`
        : `Tạm hết hàng ở lựa chọn này · SKU ${data.variant.sku}`;
    } catch (error) {
      if (id === stockRequest) { panel.classList.add('sold-out'); panel.textContent = error.message; }
    }
  }
  function renderOptions() {
    const colors = [...new Set(product.variants.map(variant => variant.color))];
    const sizes = [...new Set(product.variants.filter(variant => variant.color === color).map(variant => variant.size))];
    if (!sizes.includes(size)) size = sizes[0] || '';
    const selected = product.variants.find(item => item.color === color && item.size === size);
    $('#add-to-cart').disabled = !selected || selected.stock === 0;
    $('#add-to-cart').textContent = 'Thêm vào giỏ hàng';
    $('#selected-color').textContent = color;
    $('#selected-size').textContent = size;
    const colorBox = $('#color-options'); colorBox.replaceChildren();
    for (const value of colors) {
      const button = document.createElement('button');
      button.type = 'button'; button.textContent = value;
      button.setAttribute('aria-pressed', String(value === color));
      button.addEventListener('click', () => {
        color = value; renderOptions();
        const image = product.images.find(item => item.color === value);
        if (image) showImage(image.image, value);
        showStock();
      });
      colorBox.append(button);
    }
    const sizeBox = $('#size-options'); sizeBox.replaceChildren();
    for (const value of sizes) {
      const variant = product.variants.find(item => item.color === color && item.size === value);
      const button = document.createElement('button');
      button.type = 'button'; button.textContent = value;
      button.setAttribute('aria-pressed', String(value === size));
      button.setAttribute('aria-label', `${value}${variant.stock === 0 ? ', tạm hết hàng' : ''}`);
      if (variant.stock === 0) button.classList.add('unavailable');
      button.addEventListener('click', () => { size = value; renderOptions(); showStock(); });
      sizeBox.append(button);
    }
  }
  function sizeGuide() {
    const guide = $('#size-guide-content');
    if (product.category === 'shoes') guide.textContent = 'Cỡ giày/dép theo số EU; hãy chọn trong các cỡ thực có của mẫu này và đối chiếu với đôi bạn đang đi thoải mái nhất.';
    else if (product.category === 'trousers') guide.textContent = 'Cỡ 28 / 30 / 32 / 34 tương ứng vòng eo tham khảo khoảng 71 / 76 / 81 / 86 cm. Số đo có thể chênh lệch theo phom.';
    else if (product.sizes.includes('ONE')) guide.textContent = 'Sản phẩm có một kích cỡ. Xem mô tả và chất liệu để chọn phù hợp.';
    else guide.textContent = 'S / M / L / XL là cỡ tham khảo. Nên so sánh với món đồ cùng kiểu bạn đang mặc vừa nhất.';
  }
  async function load() {
    if (!slug || !/^[a-z0-9-]{1,100}$/.test(slug)) { $('#product-state').textContent = 'Đường dẫn sản phẩm không hợp lệ.'; return; }
    try {
      const data = await json(`/api/catalog/products/${encodeURIComponent(slug)}`);
      product = data.product;
      color = product.variants[0]?.color || '';
      size = product.variants[0]?.size || '';
      document.title = `${product.name_vi} | COGU Fashion`;
      $('#crumb-name').textContent = product.name_vi;
      $('#detail-category').textContent = names[product.category] || product.category;
      $('#detail-name').textContent = product.name_vi;
      $('#detail-price').textContent = money.format(product.price_vnd);
      $('#detail-description').textContent = product.description_vi;
      $('#detail-material').textContent = product.material;
      const gallery = $('#gallery-thumbs');
      for (const item of product.images) {
        const button = document.createElement('button');
        button.type = 'button'; button.dataset.image = item.image;
        button.setAttribute('aria-label', `Xem ảnh màu ${item.color}`);
        const img = document.createElement('img'); img.src = imageUrl(item.image); img.alt = '';
        button.append(img); button.addEventListener('click', () => showImage(item.image, item.color));
        gallery.append(button);
      }
      if (product.images.length) showImage(product.images[0].image, product.images[0].color);
      renderOptions(); sizeGuide(); showStock();
      try {
        const session = await window.CoguCommerce.current();
        if (session) {
          const saved = await window.CoguCommerce.request('/api/account/wishlist');
          favorite = saved.products.some(item => item.id === product.id);
          document.querySelector('#wish-product').textContent = favorite ? '♥ Đã yêu thích' : '♡ Yêu thích';
        }
      } catch (_) { /* Product details remain available when account status cannot load. */ }
      $('#product-state').hidden = true; $('#product-detail').hidden = false;
      if (data.related.length) {
        $('#related-grid').innerHTML = data.related.map(card).join('');
        $('#related-section').hidden = false;
      }
      const escape = window.CoguCommerce.escape;
      $('#product-reviews').innerHTML = data.reviews.length ? data.reviews.map(review => `<article class="commerce-card review-card"><strong>${escape(review.customer_name)} · ${'★'.repeat(review.rating)}</strong><span class="badge">Đã mua hàng</span><p>${escape(review.comment)}</p><small>${escape(review.created_at)}</small></article>`).join('') : '<p class="empty-state">Chưa có đánh giá được duyệt cho sản phẩm này.</p>';
      try {
        if (await window.CoguCommerce.current()) {
          const own = await window.CoguCommerce.request('/api/account/reviews');
          $('#review-form-wrap').hidden = !own.eligible_product_ids.includes(product.id) || own.reviews.some(item => item.product_id === product.id);
        }
      } catch (_) { /* Public product reviews remain visible. */ }
    } catch (error) {
      $('#product-state').textContent = error.message;
    }
  }
  document.querySelector('#add-to-cart').addEventListener('click', async event => {
    const button = event.currentTarget;
    if (!await window.CoguCommerce.current()) { window.CoguCommerce.requireAccount(); return; }
    const variant = product?.variants.find(item => item.color === color && item.size === size);
    if (!variant || variant.stock < 1) return;
    button.disabled = true;
    try {
      await window.CoguCommerce.request('/api/cart', 'POST', { variant_id: variant.id, quantity: 1 });
      document.querySelector('#purchase-status').textContent = 'Đã thêm vào giỏ hàng.';
      button.textContent = '✓ Đã thêm vào giỏ';
    } catch (error) { document.querySelector('#purchase-status').textContent = error.message; }
    finally { button.disabled = false; }
  });
  document.querySelector('#wish-product').addEventListener('click', async () => {
    if (!await window.CoguCommerce.current()) { window.CoguCommerce.requireAccount(); return; }
    try {
      await window.CoguCommerce.request(favorite ? `/api/account/wishlist/${product.id}` : '/api/account/wishlist', favorite ? 'DELETE' : 'POST', favorite ? undefined : { product_id: product.id });
      favorite = !favorite;
      document.querySelector('#wish-product').textContent = favorite ? '♥ Đã yêu thích' : '♡ Yêu thích';
      document.querySelector('#purchase-status').textContent = favorite ? 'Đã lưu vào danh sách yêu thích.' : 'Đã bỏ khỏi danh sách yêu thích.';
    } catch (error) { document.querySelector('#purchase-status').textContent = error.message; }
  });
  document.querySelector('#review-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    try {
      await window.CoguCommerce.request('/api/account/reviews', 'POST', { product_id: product.id, rating: Number(fields.get('rating')), comment: fields.get('comment') });
      $('#review-form-wrap').hidden = true;
      $('#review-status').textContent = 'Đánh giá đã được gửi và đang chờ duyệt.';
      $('#review-form-wrap').hidden = false;
      form.hidden = true;
    } catch (error) { $('#review-status').textContent = error.message; }
  });
  load();
})();
