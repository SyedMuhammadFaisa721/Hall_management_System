(() => {
  'use strict';

  const form = document.getElementById('login-form');
  const password = document.getElementById('password');
  const toggle = document.querySelector('[data-password-toggle]');
  const message = document.getElementById('form-message');

  if (!form || !password || !toggle || !message) return;

  const eyeIcon = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M2.5 12s3.3-6 9.5-6 9.5 6 9.5 6-3.3 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>';
  const hiddenIcon = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m3 3 18 18M10.6 6.2A10.5 10.5 0 0 1 12 6c6.2 0 9.5 6 9.5 6a16 16 0 0 1-2.7 3.3M6.2 6.3C3.8 7.9 2.5 12 2.5 12s3.3 6 9.5 6c1 0 1.9-.2 2.7-.5M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>';

  toggle.addEventListener('click', () => {
    const isVisible = password.type === 'text';
    password.type = isVisible ? 'password' : 'text';
    toggle.setAttribute('aria-pressed', String(!isVisible));
    toggle.setAttribute('aria-label', isVisible ? 'Show password' : 'Hide password');
    toggle.innerHTML = isVisible ? eyeIcon : hiddenIcon;
  });

  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    message.textContent = 'Sign-in is a frontend preview and is not connected to an account yet.';
    message.classList.add('visible');
  });
})();
