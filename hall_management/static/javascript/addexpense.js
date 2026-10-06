document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('add-expense-form');
  const amount = document.getElementById('expense-amount');
  const title = document.getElementById('expense-title');
  const category = document.getElementById('expense-category');
  const payer = document.getElementById('expense-paid-by');
  const feedback = document.getElementById('expense-feedback');
  const categoryPicker = document.getElementById('expense-category-picker');
  const categoryTrigger = document.getElementById('expense-category-trigger');
  const categoryMenu = document.getElementById('expense-category-options');
  const categoryOptionList = categoryMenu.querySelector('.expense-category-options');
  const categoryValue = document.getElementById('expense-category-value');
  const categoryError = document.getElementById('expense-category-error');
  const categoryOptions = Array.from(categoryMenu.querySelectorAll('[role="option"]'));
  const currency = new Intl.NumberFormat('en-PK', { maximumFractionDigits: 0 });
  let activeCategoryIndex = -1;
  let typeahead = '';
  let typeaheadTimer;

  function setActiveCategory(index) {
    activeCategoryIndex = (index + categoryOptions.length) % categoryOptions.length;
    categoryOptions.forEach(function (option, optionIndex) {
      option.classList.toggle('is-active', optionIndex === activeCategoryIndex);
    });
    categoryTrigger.setAttribute('aria-activedescendant', categoryOptions[activeCategoryIndex].id);
  }

  function positionCategoryMenu() {
    const bounds = categoryTrigger.getBoundingClientRect();
    const gap = 7;
    const padding = 10;
    const spaceBelow = window.innerHeight - bounds.bottom - gap - padding;
    const spaceAbove = bounds.top - gap - padding;
    const initialHeight = categoryMenu.getBoundingClientRect().height;
    const openAbove = spaceBelow < initialHeight && spaceAbove > spaceBelow;
    const availableSpace = Math.max(120, openAbove ? spaceAbove : spaceBelow);
    categoryOptionList.style.maxHeight = Math.max(90, Math.min(window.innerHeight * 0.55, availableSpace - 48)) + 'px';
    const menuHeight = categoryMenu.getBoundingClientRect().height;
    const top = openAbove
      ? Math.max(padding, bounds.top - Math.min(menuHeight, spaceAbove) - gap)
      : Math.min(bounds.bottom + gap, window.innerHeight - menuHeight - padding);
    categoryMenu.style.top = top + 'px';
    categoryMenu.style.left = Math.max(padding, Math.min(bounds.left, window.innerWidth - bounds.width - padding)) + 'px';
    categoryMenu.style.width = Math.min(bounds.width, window.innerWidth - padding * 2) + 'px';
  }

  function openCategoryMenu(index) {
    document.body.append(categoryMenu);
    categoryMenu.hidden = false;
    categoryPicker.classList.add('is-open');
    categoryTrigger.setAttribute('aria-expanded', 'true');
    positionCategoryMenu();
    const selectedIndex = categoryOptions.findIndex(function (option) {
      return option.dataset.value === category.value;
    });
    setActiveCategory(index ?? (selectedIndex >= 0 ? selectedIndex : 0));
  }

  function closeCategoryMenu() {
    categoryMenu.hidden = true;
    categoryPicker.classList.remove('is-open');
    categoryTrigger.setAttribute('aria-expanded', 'false');
    categoryTrigger.removeAttribute('aria-activedescendant');
    categoryOptions.forEach(function (option) {
      option.classList.remove('is-active');
    });
    activeCategoryIndex = -1;
  }

  function chooseCategory(option) {
    category.value = option.dataset.value;
    categoryValue.textContent = option.dataset.value;
    categoryTrigger.setAttribute('aria-invalid', 'false');
    categoryError.textContent = '';
    categoryOptions.forEach(function (item) {
      item.setAttribute('aria-selected', String(item === option));
    });
    category.dispatchEvent(new Event('change', { bubbles: true }));
    closeCategoryMenu();
    categoryTrigger.focus();
  }

  categoryTrigger.addEventListener('click', function () {
    if (categoryMenu.hidden) openCategoryMenu();
    else closeCategoryMenu();
  });

  categoryTrigger.addEventListener('keydown', function (event) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (categoryMenu.hidden) openCategoryMenu();
      else setActiveCategory(activeCategoryIndex + (event.key === 'ArrowDown' ? 1 : -1));
    } else if ((event.key === 'Enter' || event.key === ' ') && !categoryMenu.hidden) {
      event.preventDefault();
      chooseCategory(categoryOptions[activeCategoryIndex]);
    } else if (event.key === 'Escape' && !categoryMenu.hidden) {
      event.preventDefault();
      closeCategoryMenu();
    } else if (event.key === 'Tab' && !categoryMenu.hidden) {
      closeCategoryMenu();
    } else if (event.key === 'Home' && !categoryMenu.hidden) {
      event.preventDefault();
      setActiveCategory(0);
    } else if (event.key === 'End' && !categoryMenu.hidden) {
      event.preventDefault();
      setActiveCategory(categoryOptions.length - 1);
    } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
      typeahead += event.key.toLowerCase();
      window.clearTimeout(typeaheadTimer);
      typeaheadTimer = window.setTimeout(function () { typeahead = ''; }, 600);
      const matchIndex = categoryOptions.findIndex(function (option) {
        return option.dataset.value.toLowerCase().startsWith(typeahead);
      });
      if (matchIndex >= 0) {
        if (categoryMenu.hidden) openCategoryMenu(matchIndex);
        else setActiveCategory(matchIndex);
      }
    }
  });

  categoryOptions.forEach(function (option, index) {
    option.addEventListener('pointerenter', function () {
      if (!categoryMenu.hidden) setActiveCategory(index);
    });
    option.addEventListener('click', function () {
      chooseCategory(option);
    });
  });

  document.addEventListener('pointerdown', function (event) {
    if (!categoryPicker.contains(event.target) && !categoryMenu.contains(event.target) && !categoryMenu.hidden) closeCategoryMenu();
  });

  window.addEventListener('resize', function () {
    if (!categoryMenu.hidden) closeCategoryMenu();
  });
  window.addEventListener('scroll', function (event) {
    if (!categoryMenu.hidden && !categoryMenu.contains(event.target)) closeCategoryMenu();
  }, true);

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
    if (!category.value) {
      categoryTrigger.setAttribute('aria-invalid', 'true');
      categoryError.textContent = 'Choose an expense category to continue.';
      categoryTrigger.focus();
      return;
    }
    if (!form.reportValidity()) return;
    feedback.textContent = 'Preview only: connect a backend to save this expense.';
  });
});
