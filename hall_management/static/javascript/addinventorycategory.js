document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('add-inventory-category-form');
  const name = document.getElementById('category-name');
  const previewName = document.getElementById('category-preview-name');
  const characterCount = document.getElementById('category-name-count');
  const feedback = document.getElementById('category-feedback');

  function updatePreview() {
    const value = name.value.trim();
    previewName.textContent = value || 'Category name';
    characterCount.textContent = name.value.length + ' / 20';
  }

  document.querySelectorAll('.inventory-category-chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      name.value = chip.dataset.category;
      updatePreview();
      name.focus();
      feedback.textContent = '';
    });
  });

  name.addEventListener('input', updatePreview);
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    updatePreview();
    if (!form.reportValidity()) return;
    feedback.textContent = 'Preview only: connect a backend to save this category.';
  });
});