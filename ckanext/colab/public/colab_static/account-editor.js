(function () {
  'use strict';
  var form = document.getElementById('account-edit-form');
  if (!form) return;
  var preview = document.getElementById('account-changes');
  function updatePreview() {
    var list = preview.querySelector('ul');
    list.replaceChildren();
    form.querySelectorAll('input[data-original]').forEach(function (input) {
      if (input.value.trim() === input.dataset.original) return;
      var item = document.createElement('li');
      var label = form.querySelector('label[for="' + input.id + '"]');
      item.textContent = label.textContent + ': ' + (input.dataset.original || '—') + ' → ' + (input.value.trim() || '—');
      list.appendChild(item);
    });
    preview.hidden = !list.children.length;
  }
  form.addEventListener('input', updatePreview);
  updatePreview();
}());
