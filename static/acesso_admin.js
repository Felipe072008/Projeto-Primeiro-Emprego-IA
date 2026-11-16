// O servidor controla PIN, autorização temporária, tentativas e autenticação.
(() => {
  const trigger = document.querySelector('#restricted-access');
  const pinDialog = document.querySelector('#admin-pin-dialog');
  const loginDialog = document.querySelector('#admin-login-dialog');
  let csrf = '';
  async function call(path, data) {
    const response = await fetch(path, {method: data ? 'POST' : 'GET', credentials: 'same-origin',
      headers: {'Content-Type':'application/json','X-Requested-With':'FirstJob','X-CSRF-Token':csrf},
      body: data ? JSON.stringify(data) : undefined});
    const result = await response.json();
    if (!response.ok) throw new Error('Dados inválidos');
    if (result.csrf) csrf = result.csrf;
    return result;
  }
  trigger.addEventListener('click', async () => {
    trigger.disabled = true;
    try {
      await call('/admin-access');
      pinDialog.querySelector('form').reset();
      pinDialog.querySelector('[role=alert]').textContent = '';
      pinDialog.showModal();
    } catch {
      pinDialog.querySelector('[role=alert]').textContent = 'Dados inválidos';
      pinDialog.showModal();
    } finally { trigger.disabled = false; }
  });
  for (const [dialog, kind] of [[pinDialog,'pin'],[loginDialog,'login']]) {
    const form = dialog.querySelector('form');
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const button = form.querySelector('[type=submit]');
      button.disabled = true;
      try {
        const result = await call('/admin-access/' + kind, Object.fromEntries(new FormData(form)));
        form.reset();
        dialog.close();
        if (kind === 'pin') {
          loginDialog.querySelector('form').reset();
          loginDialog.querySelector('[role=alert]').textContent = '';
          loginDialog.showModal();
        } else { window.location.assign(result.next); }
      } catch { form.querySelector('[role=alert]').textContent = 'Dados inválidos'; }
      finally { button.disabled = false; }
    });
    dialog.querySelector('[data-close-admin]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => { form.reset(); trigger.focus(); });
    dialog.addEventListener('keydown', event => {
      if (event.key === 'Escape') event.stopPropagation();
      if (event.key !== 'Tab') return;
      const focusable = [...dialog.querySelectorAll('input,button')].filter(el => !el.disabled);
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
  }
})();
