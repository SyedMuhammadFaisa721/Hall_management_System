document.addEventListener('DOMContentLoaded', function () {
  const search = document.getElementById('inventory-search');
  const category = document.getElementById('inventory-category-filter');
  const stock = document.getElementById('inventory-stock-filter');
  const rows = Array.from(document.querySelectorAll('#inventory-rows tr'));
  const emptyState = document.getElementById('inventory-empty-state');
  const resultCount = document.getElementById('inventory-result-count');

  function filterInventory() {
    const query = search.value.trim().toLowerCase();
    let visibleCount = 0;
    rows.forEach(function (row) {
      const matchesQuery = row.textContent.toLowerCase().includes(query);
      const matchesCategory = category.value === 'all' || row.dataset.category === category.value;
      const matchesStock = stock.value === 'all' || row.dataset.stock === stock.value;
      const visible = matchesQuery && matchesCategory && matchesStock;
      row.hidden = !visible;
      if (visible) visibleCount += 1;
    });
    emptyState.hidden = visibleCount !== 0;
    resultCount.textContent = 'Showing ' + visibleCount + ' stock item' + (visibleCount === 1 ? '' : 's');
  }

  search.addEventListener('input', filterInventory);
  category.addEventListener('change', filterInventory);
  stock.addEventListener('change', filterInventory);
});
