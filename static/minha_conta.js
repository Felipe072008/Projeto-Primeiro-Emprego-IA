// Usa a navegação, mensagens e proteção de requisições já existentes no site.
async function loadMyAccount() {
  try {
    const data = await api('/api/account/profile');
    $('#account-name-form [name=name]').value = data.user.name;
    $('#account-current-email').textContent = data.user.email;
    $('#account-created').textContent = formatTime(data.user.created_at) || 'Não registrado';
    $('#account-last-login').textContent = formatTime(data.user.last_login_at) || 'Não registrado';
    $('#account-terms').textContent = data.terms.length ? data.terms.map(term => `Termos aceitos: versão ${term.terms_version}, em ${formatTime(term.accepted_at)}.`).join(' ') : 'Não há registro de aceite dos Termos para esta conta.';
  } catch (error) { toast(error.message, 'error'); }
}

function finishAccountSession(message) {
  state.me = null;
  $$('#page-account form').forEach(form => form.reset());
  switchView(false);
  toggleAuth('login');
  history.replaceState(null, '', location.pathname);
  $('#login-form [name=email]').focus();
  toast(message);
}

function bindAccountEvents() {
  $$('[data-password-toggle]').forEach(button => button.addEventListener('click', () => {
    const input = document.getElementById(button.dataset.passwordToggle);
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    button.textContent = show ? 'Ocultar' : 'Mostrar';
    button.setAttribute('aria-pressed', String(show));
    button.setAttribute('aria-label', button.getAttribute('aria-label').replace(show ? 'Mostrar' : 'Ocultar', show ? 'Ocultar' : 'Mostrar'));
  }));
  for (const [id, endpoint, method] of [['name','profile','PATCH'],['email','email','POST'],['password','password','POST'],['export','export','POST'],['delete','delete','POST']]) {
    const form = $(`#account-${id}-form`);
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const button = form.querySelector('[type=submit]'), status = form.querySelector('[role=status]');
      if (button.disabled) return;
      button.disabled = true; status.textContent = 'Processando…';
      try {
        const data = Object.fromEntries(new FormData(form));
        if (id === 'export') {
          const response = await fetch('/api/account/export', {method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Requested-With':'FirstJob'},body:JSON.stringify(data)});
          if (!response.ok) { const error = await response.json(); throw new Error(error.error || 'Não foi possível baixar seus dados.'); }
          const url = URL.createObjectURL(await response.blob());
          const link = document.createElement('a'); link.href = url; link.download = 'meus-dados.zip';
          document.body.append(link); link.click(); link.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000);
          status.textContent = 'Download preparado.'; form.reset();
        } else {
          const result = await api('/api/account/' + endpoint,{method,body:data});
          form.reset(); status.textContent = result.message;
          if (result.user) { state.me.user = {...state.me.user,...result.user}; accountDetails(); await loadMyAccount(); }
          if (id === 'delete') finishAccountSession(result.message);
        }
      } catch (error) { status.textContent = error.message; }
      finally { button.disabled = false; }
    });
  }
  $('#account-end-sessions').addEventListener('click',async event => {
    const button = event.currentTarget; button.disabled = true;
    try { const result = await api('/api/account/sessions',{method:'POST',body:{}}); finishAccountSession(result.message); }
    catch(error) { $('#account-sessions-status').textContent = error.message; }
    finally { button.disabled = false; }
  });
}
