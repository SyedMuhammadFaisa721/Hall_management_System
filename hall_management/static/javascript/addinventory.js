document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('add-inventory-form');
  const total = document.getElementById('inventory-total');
  const available = document.getElementById('inventory-available');
  const damaged = document.getElementById('inventory-damaged');
  const name = document.getElementById('inventory-name');
  const category = document.getElementById('inventory-category');
  const feedback = document.getElementById('inventory-feedback');

  function updatePreview() {
    const totalCount = Number(total.value) || 0;
    const availableCount = Number(available.value) || 0;
    const damagedCount = Number(damaged.value) || 0;
    const hasOverflow = availableCount + damagedCount > totalCount;
    document.getElementById('inventory-preview-name').textContent = name.value.trim() || 'New inventory item';
    document.getElementById('inventory-preview-category').textContent = category.value || 'Not selected';
    document.getElementById('inventory-preview-total').textContent = totalCount.toLocaleString();
    document.getElementById('inventory-preview-available').textContent = availableCount.toLocaleString();
    document.getElementById('inventory-preview-damaged').textContent = damagedCount.toLocaleString();
    document.getElementById('inventory-stock-percent').textContent = hasOverflow ? 'Check counts' : (totalCount ? Math.round(availableCount / totalCount * 100) : 0) + '%';
    document.getElementById('inventory-stock-fill').style.width = Math.min(totalCount ? availableCount / totalCount * 100 : 0, 100) + '%';
    damaged.setCustomValidity(hasOverflow ? 'Available and damaged quantities cannot exceed total quantity.' : '');
  }

  form.addEventListener('input', updatePreview);
  form.addEventListener('change', updatePreview);
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    updatePreview();
    if (!form.reportValidity()) return;
    feedback.textContent = 'Preview only: connect a backend to save this inventory item.';
  });
});
