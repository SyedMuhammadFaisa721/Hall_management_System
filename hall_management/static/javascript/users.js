document.addEventListener('DOMContentLoaded', function () {
  const search = document.getElementById('user-search');
  const roleFilter = document.getElementById('user-role-filter');
  const statusFilter = document.getElementById('user-status-filter');
  const list = document.getElementById('users-list');
  const count = document.getElementById('user-result-count');
  const noResults = document.getElementById('users-no-results');

  if (!search || !roleFilter || !statusFilter || !list || !count || !noResults) return;

  const rows = Array.from(list.querySelectorAll('.user-row'));

  function updateUsers() {
    const query = search.value.trim().toLowerCase();
    const role = roleFilter.value;
    const status = statusFilter.value;
    let visibleCount = 0;

    rows.forEach(function (row) {
      const matchesSearch = row.textContent.toLowerCase().includes(query);
      const matchesRole = role === 'all' || row.dataset.role === role;
      const matchesStatus = status === 'all' || row.dataset.status === status;
      const isVisible = matchesSearch && matchesRole && matchesStatus;
      row.hidden = !isVisible;
      if (isVisible) visibleCount += 1;
    });

    noResults.hidden = rows.length === 0 || visibleCount > 0;
    count.textContent = visibleCount === rows.length
      ? 'Showing ' + visibleCount + (visibleCount === 1 ? ' user' : ' users')
      : 'Showing ' + visibleCount + ' of ' + rows.length + ' users';
  }

  search.addEventListener('input', updateUsers);
  roleFilter.addEventListener('change', updateUsers);
  statusFilter.addEventListener('change', updateUsers);
});