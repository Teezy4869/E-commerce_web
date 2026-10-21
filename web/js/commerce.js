(() => {
  'use strict';
  const money = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 });
  const escape = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
  let session = null;
  async function request(path, method = 'GET', body) {
    const headers = { Accept: 'application/json' };
    if (method !== 'GET') {
      headers['Content-Type'] = 'application/json';
      if (session?.csrf_token) headers['X-CSRF-Token'] = session.csrf_token;
    }
    const response = await fetch(path, { method, credentials: 'same-origin', headers,
      body: method === 'GET' ? undefined : JSON.stringify(body || {}) });
    const data = await response.json();
    if (!response.ok) {
      const error = new Error(data.message || `Yêu cầu thất bại (${response.status})`);
      error.status = response.status;
      throw error;
    }
    return data;
  }
  async function current() {
    if (session) return session;
    try { session = await request('/api/auth/me'); return session; }
    catch (error) { if (error.status === 401) return null; throw error; }
  }
  function setSession(value) { session = value; }
  function accountReturn() { return '/account?return=' + encodeURIComponent(location.pathname + location.search); }
  function requireAccount() { location.href = accountReturn(); }
  window.CoguCommerce = { request, current, setSession, requireAccount, money, escape };
})();
