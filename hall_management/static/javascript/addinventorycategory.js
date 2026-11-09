document.addEventListener('DOMContentLoaded', function () {
  const name = document.getElementById('category-name');
  const previewName = document.getElementById('category-preview-name');
  const characterCount = document.getElementById('category-name-count');

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
    });
  });

  name.addEventListener('input', updatePreview);
});