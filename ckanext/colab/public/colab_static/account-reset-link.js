(function () {
  'use strict';
  var copy = document.getElementById('copy-reset-link');
  if (copy) copy.addEventListener('click', async function () {
    var input = document.getElementById('password-reset-link');
    var status = document.getElementById('reset-copy-status');
    try {
      await navigator.clipboard.writeText(input.value);
      status.textContent = copy.dataset.success;
    } catch (error) {
      input.focus();
      input.select();
      status.textContent = copy.dataset.fallback;
    }
  });
  var form = document.querySelector('.account-reset-form');
  if (form) form.addEventListener('submit', function () {
    form.querySelector('button[type="submit"]').disabled = true;
  });
}());
