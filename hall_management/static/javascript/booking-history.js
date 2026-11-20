document.addEventListener('DOMContentLoaded', function () {
  const root = document.querySelector('#booking-history');
  if (!root) return;

  const rows = Array.from(root.querySelectorAll('[data-history-year]'));
  const rangeButtons = Array.from(root.querySelectorAll('[data-history-range]'));
  const numberFormat = new Intl.NumberFormat();
  const currentYear = Math.max(...rows.map(row => Number(row.dataset.historyYear)));

  function updateHistory(range) {
    const firstYear = currentYear - range + 1;
    let total = 0;
    let confirmed = 0;
    let cancelled = 0;
    let visibleYears = 0;

    rows.forEach(row => {
      const year = Number(row.dataset.historyYear);
      const rowTotal = Number(row.dataset.total);
      const rowConfirmed = Number(row.dataset.confirmed);
      const rowCancelled = Number(row.dataset.cancelled);
      const visible = year >= firstYear && year <= currentYear;
      row.hidden = !visible;
      if (!visible) return;

      total += rowTotal;
      confirmed += rowConfirmed;
      cancelled += rowCancelled;
      visibleYears += 1;

      const confirmedBar = row.querySelector('.history-mix-confirmed');
      const cancelledBar = row.querySelector('.history-mix-cancelled');
      const mix = row.querySelector('.history-mix');
      confirmedBar.style.width = `${rowTotal ? rowConfirmed / rowTotal * 100 : 0}%`;
      cancelledBar.style.width = `${rowTotal ? rowCancelled / rowTotal * 100 : 0}%`;
      mix.setAttribute(
        'aria-label',
        `${rowConfirmed} confirmed, ${rowCancelled} cancelled, ${rowTotal} total`,
      );
    });

    root.querySelector('[data-history-total]').textContent = numberFormat.format(total);
    root.querySelector('[data-history-confirmed]').textContent = numberFormat.format(confirmed);
    root.querySelector('[data-history-cancelled]').textContent = numberFormat.format(cancelled);
    root.querySelector('[data-history-rate]').textContent =
      `${total ? Math.round(confirmed / total * 100) : 0}%`;
    root.querySelector('[data-history-period]').textContent = `${firstYear}–${currentYear}`;
    root.querySelector('[data-history-chip]').textContent = `Last ${range} years`;
    root.querySelector('[data-history-count]').textContent = `Showing ${visibleYears} years`;

    rangeButtons.forEach(button => {
      button.setAttribute('aria-pressed', String(Number(button.dataset.historyRange) === range));
    });
  }

  rangeButtons.forEach(button => {
    button.addEventListener('click', function () {
      updateHistory(Number(button.dataset.historyRange));
    });
  });

  updateHistory(20);
});
