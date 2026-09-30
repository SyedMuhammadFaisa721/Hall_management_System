document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('add-expense-form');
  const amount = document.getElementById('expense-amount');
  const title = document.getElementById('expense-title');
  const category = document.getElementById('expense-category');
  const payer = document.getElementById('expense-paid-by');
  const feedback = document.getElementById('expense-feedback');
  const currency = new Intl.NumberFormat('en-PK', { maximumFractionDigits: 0 });

  function updatePreview() {
    document.getElementById('expense-preview-amount').textContent = 'Rs ' + currency.format(Number(amount.value) || 0);
    document.getElementById('expense-preview-title').textContent = title.value.trim() || 'New expense';
    document.getElementById('expense-preview-category').textContent = category.value || 'Not selected';
    document.getElementById('expense-preview-payer').textContent = payer.value.trim() || 'Not entered';
    document.getElementById('expense-preview-status').textContent = form.querySelector('input[name="status"]:checked').value;
  }

  form.addEventListener('input', updatePreview);
  form.addEventListener('change', updatePreview);
  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!form.reportValidity()) return;
    feedback.textContent = 'Preview only: connect a backend to save this expense.';
  });
});
