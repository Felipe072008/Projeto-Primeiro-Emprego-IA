/* O consentimento fica neste navegador. Nenhum rastreador é instalado por este módulo. */
(() => {
  'use strict';
  const script = document.querySelector('script[data-cookie-version]');
  const version = script.dataset.cookieVersion;
  const key = 'primeiroemprego.cookie_preferences';
  const lifetime = Number(script.dataset.cookieDays) * 86400000;
  const banner = document.querySelector('#cookie-banner');
  const dialog = document.querySelector('#cookie-dialog');
  const status = document.querySelector('#cookie-status');
  const functionality = document.querySelector('#cookie-functionality');
  let returnFocus = null;

  function readPreferences() {
    try {
      const data = JSON.parse(localStorage.getItem(key));
      const saved = Date.parse(data?.saved_at), expires = Date.parse(data?.expires_at);
      if (data?.version !== version || data.necessary !== true || typeof data.functionality !== 'boolean'
          || data.analytics !== false || data.marketing !== false || !Number.isFinite(saved)
          || !Number.isFinite(expires) || saved > Date.now() || expires <= Date.now()
          || expires - saved !== lifetime) { localStorage.removeItem(key); return null; }
      return data;
    } catch { return null; }
  }

  let preferences = readPreferences();
  function clearOptionalStorage() {
    // Estes são os únicos dados opcionais controlados pelo site; a sessão de login é preservada.
    try { sessionStorage.removeItem('filters-jobs'); sessionStorage.removeItem('filters-courses'); } catch {}
  }
  function applyPreferences() {
    if (!preferences?.functionality) clearOptionalStorage();
    functionality.checked = preferences?.functionality === true;
    banner.hidden = preferences !== null;
    window.dispatchEvent(new CustomEvent('cookiepreferenceschange', {detail: {functionality: preferences?.functionality === true}}));
  }
  function closePreferences() {
    if (dialog.open) dialog.close();
    if (returnFocus?.isConnected && returnFocus.getClientRects().length) returnFocus.focus();
  }
  function savePreferences(values) {
    const now = Date.now();
    preferences = {version, necessary: true, analytics: false, functionality: values.functionality === true,
                   marketing: false, saved_at: new Date(now).toISOString(), expires_at: new Date(now + lifetime).toISOString()};
    let persisted = true;
    try { localStorage.setItem(key, JSON.stringify(preferences)); } catch { persisted = false; }
    applyPreferences();
    closePreferences();
    status.textContent = persisted ? 'Preferências de cookies salvas. Você pode alterá-las no rodapé.' :
      'Preferências aplicadas nesta página. O navegador impediu salvar; o aviso poderá reaparecer.';
  }
  function openPreferences() {
    returnFocus = document.activeElement;
    functionality.checked = preferences?.functionality === true;
    if (!dialog.open) dialog.showModal();
    dialog.querySelector('[data-cookie-close]').focus();
  }
  // A interface consulta este estado antes de ler ou gravar filtros opcionais.
  window.sitePrivacy = Object.freeze({allows: category => category === 'necessary' ||
      (category === 'functionality' && preferences?.functionality === true), open: openPreferences});
  document.addEventListener('click', event => {
    if (event.target.closest('[data-cookie-open]')) { event.preventDefault(); openPreferences(); }
    const action = event.target.closest('[data-cookie-action]')?.dataset.cookieAction;
    if (action === 'accept') savePreferences({functionality: true});
    if (action === 'reject') savePreferences({functionality: false});
    if (event.target.closest('[data-cookie-close]')) closePreferences();
  });
  document.querySelector('#cookie-preferences-form').addEventListener('submit', event => {
    event.preventDefault(); savePreferences({functionality: functionality.checked});
  });
  dialog.addEventListener('cancel', event => { event.preventDefault(); closePreferences(); });
  dialog.addEventListener('keydown', event => {
    event.stopPropagation();
    if (event.key !== 'Tab') return;
    const controls = [...dialog.querySelectorAll('button:not(:disabled), a[href], input:not(:disabled)')];
    const first = controls[0], last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) { preferences = readPreferences(); applyPreferences(); }
  });
  applyPreferences();
})();
