document.addEventListener('DOMContentLoaded', function () {
  const enhancedSelects = Array.from(document.querySelectorAll('select')).filter(function (select) {
    return !select.multiple && select.size <= 1 && !select.disabled &&
      !select.classList.contains('expense-category-native') &&
      !select.closest('.booking-form-field');
  });
  let activePicker = null;

  function closePicker(returnFocus) {
    if (!activePicker) return;
    const picker = activePicker;
    picker.menu.hidden = true;
    picker.wrapper.classList.remove('is-open');
    picker.trigger.setAttribute('aria-expanded', 'false');
    picker.trigger.removeAttribute('aria-activedescendant');
    picker.options.forEach(function (option) { option.classList.remove('is-active'); });
    activePicker = null;
    if (returnFocus) picker.trigger.focus();
  }

  function syncPicker(picker) {
    const selectedOption = picker.select.options[picker.select.selectedIndex];
    picker.value.textContent = selectedOption ? selectedOption.textContent.trim() : 'Choose an option';
    picker.trigger.setAttribute('aria-label', picker.label + ': ' + picker.value.textContent);
    picker.options.forEach(function (option, index) {
      option.setAttribute('aria-selected', String(index === picker.select.selectedIndex));
    });
    if (picker.select.value) picker.trigger.setAttribute('aria-invalid', 'false');
  }

  function focusOption(picker, index) {
    const enabledOptions = picker.options.filter(function (option) {
      return option.getAttribute('aria-disabled') !== 'true';
    });
    if (!enabledOptions.length) return;
    let optionIndex = ((index % picker.options.length) + picker.options.length) % picker.options.length;
    for (let checked = 0; checked < picker.options.length; checked += 1) {
      if (picker.options[optionIndex].getAttribute('aria-disabled') !== 'true') break;
      optionIndex = (optionIndex + 1) % picker.options.length;
    }
    const option = picker.options[optionIndex];
    picker.activeIndex = optionIndex;
    picker.options.forEach(function (item, optionIndex) {
      item.classList.toggle('is-active', optionIndex === picker.activeIndex);
    });
    picker.trigger.setAttribute('aria-activedescendant', option.id);
    option.scrollIntoView({ block: 'nearest' });
  }

  function positionMenu(picker) {
    const bounds = picker.trigger.getBoundingClientRect();
    const gap = 6;
    const viewportPadding = 10;
    picker.menu.style.width = Math.min(bounds.width, window.innerWidth - viewportPadding * 2) + 'px';
    picker.menu.style.maxHeight = Math.max(120, window.innerHeight - viewportPadding * 2) + 'px';
    const menuHeight = picker.menu.getBoundingClientRect().height;
    const spaceBelow = window.innerHeight - bounds.bottom - gap - viewportPadding;
    const spaceAbove = bounds.top - gap - viewportPadding;
    const openAbove = spaceBelow < menuHeight && spaceAbove > spaceBelow;
    const top = openAbove
      ? Math.max(viewportPadding, bounds.top - Math.min(menuHeight, spaceAbove) - gap)
      : Math.min(bounds.bottom + gap, window.innerHeight - menuHeight - viewportPadding);
    const left = Math.max(viewportPadding, Math.min(bounds.left, window.innerWidth - bounds.width - viewportPadding));
    picker.menu.style.top = top + 'px';
    picker.menu.style.left = left + 'px';
  }

  function openPicker(picker) {
    closePicker(false);
    picker.menu.hidden = false;
    picker.wrapper.classList.add('is-open');
    picker.trigger.setAttribute('aria-expanded', 'true');
    activePicker = picker;
    positionMenu(picker);
    const selectedIndex = picker.select.selectedIndex;
    const selectedOption = picker.options[selectedIndex];
    focusOption(picker, selectedOption && selectedOption.getAttribute('aria-disabled') !== 'true'
      ? selectedIndex
      : picker.options.findIndex(function (option) { return option.getAttribute('aria-disabled') !== 'true'; }));
  }

  enhancedSelects.forEach(function (select, pickerIndex) {
    const wrapper = document.createElement('div');
    wrapper.className = 'hm-select-wrap';
    if (select.classList.contains('select-compact')) wrapper.classList.add('is-compact');

    const trigger = document.createElement('button');
    const triggerId = 'hm-select-trigger-' + pickerIndex;
    const valueId = 'hm-select-value-' + pickerIndex;
    trigger.type = 'button';
    trigger.id = triggerId;
    trigger.className = 'hm-select-trigger';
    trigger.setAttribute('role', 'combobox');
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.setAttribute('aria-controls', 'hm-select-menu-' + pickerIndex);
    trigger.setAttribute('aria-required', String(select.required));
    trigger.setAttribute('aria-invalid', 'false');

    const value = document.createElement('span');
    value.id = valueId;
    value.className = 'hm-select-value';
    trigger.append(value);

    const chevron = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    chevron.setAttribute('viewBox', '0 0 24 24');
    chevron.setAttribute('fill', 'none');
    chevron.setAttribute('stroke', 'currentColor');
    chevron.setAttribute('stroke-width', '1.8');
    chevron.setAttribute('stroke-linecap', 'round');
    chevron.setAttribute('stroke-linejoin', 'round');
    chevron.setAttribute('aria-hidden', 'true');
    chevron.classList.add('hm-select-chevron');
    const chevronPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    chevronPath.setAttribute('d', 'm7 10 5 5 5-5');
    chevron.append(chevronPath);
    trigger.append(chevron);

    const menu = document.createElement('div');
    menu.id = 'hm-select-menu-' + pickerIndex;
    menu.className = 'hm-select-menu';
    menu.setAttribute('role', 'listbox');
    menu.hidden = true;

    const optionsContainer = document.createElement('div');
    optionsContainer.className = 'hm-select-options';
    const options = Array.from(select.options).map(function (nativeOption, optionIndex) {
      const option = document.createElement('div');
      option.id = menu.id + '-option-' + optionIndex;
      option.className = 'hm-select-option';
      option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', String(optionIndex === select.selectedIndex));
      option.setAttribute('aria-disabled', String(nativeOption.disabled));

      const mark = document.createElement('span');
      mark.className = 'hm-select-option-mark';
      mark.setAttribute('aria-hidden', 'true');
      mark.textContent = nativeOption.textContent.trim().charAt(0).toUpperCase();

      const label = document.createElement('span');
      label.className = 'hm-select-option-label';
      label.textContent = nativeOption.textContent.trim();

      const check = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      check.setAttribute('viewBox', '0 0 24 24');
      check.setAttribute('fill', 'none');
      check.setAttribute('stroke', 'currentColor');
      check.setAttribute('stroke-width', '2');
      check.setAttribute('stroke-linecap', 'round');
      check.setAttribute('stroke-linejoin', 'round');
      check.setAttribute('aria-hidden', 'true');
      check.classList.add('hm-select-option-check');
      const checkPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      checkPath.setAttribute('d', 'm5 12 4 4L19 6');
      check.append(checkPath);

      option.append(mark, label, check);
      option.addEventListener('pointerenter', function () {
        if (activePicker === picker && !nativeOption.disabled) focusOption(picker, optionIndex);
      });
      option.addEventListener('click', function () {
        if (nativeOption.disabled) return;
        select.selectedIndex = optionIndex;
        select.dispatchEvent(new Event('input', { bubbles: true }));
        select.dispatchEvent(new Event('change', { bubbles: true }));
        syncPicker(picker);
        closePicker(true);
      });
      optionsContainer.append(option);
      return option;
    });

    const heading = document.createElement('div');
    heading.className = 'hm-select-menu-heading';
    const labels = Array.from(select.labels || []);
    const labelText = (select.getAttribute('aria-label') || (labels[0] && labels[0].textContent) || select.name || 'Choose an option').trim();
    const headingLabel = document.createElement('span');
    headingLabel.textContent = labelText;
    const count = document.createElement('span');
    count.className = 'hm-select-menu-count';
    count.textContent = options.length + ' OPTIONS';
    heading.append(headingLabel, count);
    menu.append(heading, optionsContainer);

    const picker = { select, wrapper, trigger, value, menu, options, label: labelText, activeIndex: -1 };
    wrapper.append(select, trigger);
    select.parentNode.insertBefore(wrapper, select);
    select.classList.add('hm-select-native');
    select.setAttribute('aria-hidden', 'true');
    select.tabIndex = -1;
    trigger.setAttribute('aria-labelledby', labels[0] ? labels[0].id || valueId : valueId);
    if (labels[0] && !labels[0].id) {
      labels[0].id = 'hm-select-label-' + pickerIndex;
      trigger.setAttribute('aria-labelledby', labels[0].id + ' ' + valueId);
    } else if (labels[0]) {
      trigger.setAttribute('aria-labelledby', labels[0].id + ' ' + valueId);
    } else {
      trigger.setAttribute('aria-label', labelText);
    }
    labels.forEach(function (label) {
      if (label.htmlFor === select.id) label.htmlFor = triggerId;
      if (!label.htmlFor && label.contains(select)) {
        label.addEventListener('click', function (event) {
          if (event.target !== trigger && !trigger.contains(event.target)) {
            event.preventDefault();
            trigger.focus();
          }
        });
      }
    });
    document.body.append(menu);
    syncPicker(picker);

    trigger.addEventListener('click', function () {
      if (activePicker === picker) closePicker(false);
      else openPicker(picker);
    });
    trigger.addEventListener('keydown', function (event) {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        if (activePicker !== picker) openPicker(picker);
        else focusOption(picker, picker.activeIndex + (event.key === 'ArrowDown' ? 1 : -1));
      } else if ((event.key === 'Enter' || event.key === ' ') && activePicker === picker) {
        event.preventDefault();
        options[picker.activeIndex]?.click();
      } else if ((event.key === 'Enter' || event.key === ' ') && activePicker !== picker) {
        event.preventDefault();
        openPicker(picker);
      } else if (event.key === 'Escape' && activePicker === picker) {
        event.preventDefault();
        closePicker(false);
      } else if (event.key === 'Tab' && activePicker === picker) {
        closePicker(false);
      } else if (event.key === 'Home' && activePicker === picker) {
        event.preventDefault();
        focusOption(picker, 0);
      } else if (event.key === 'End' && activePicker === picker) {
        event.preventDefault();
        focusOption(picker, options.length - 1);
      } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
        picker.typeahead = (picker.typeahead || '') + event.key.toLowerCase();
        window.clearTimeout(picker.typeaheadTimer);
        picker.typeaheadTimer = window.setTimeout(function () { picker.typeahead = ''; }, 600);
        const matchIndex = select.options.findIndex(function (option) {
          return !option.disabled && option.textContent.trim().toLowerCase().startsWith(picker.typeahead);
        });
        if (matchIndex >= 0) {
          if (activePicker !== picker) openPicker(picker);
          focusOption(picker, matchIndex);
        }
      }
    });
    menu.addEventListener('keydown', function (event) {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        focusOption(picker, picker.activeIndex + (event.key === 'ArrowDown' ? 1 : -1));
      } else if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault();
        focusOption(picker, event.key === 'Home' ? 0 : options.length - 1);
      } else if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        options[picker.activeIndex]?.click();
      } else if (event.key === 'Escape') {
        event.preventDefault();
        closePicker(true);
      } else if (event.key === 'Tab') {
        closePicker(false);
      }
    });
    select.addEventListener('change', function () { syncPicker(picker); });
    select.addEventListener('invalid', function (event) {
      event.preventDefault();
      trigger.setAttribute('aria-invalid', 'true');
      trigger.focus();
    });
    select.form?.addEventListener('reset', function () {
      window.setTimeout(function () {
        syncPicker(picker);
        trigger.setAttribute('aria-invalid', 'false');
      });
    });
  });

  document.addEventListener('pointerdown', function (event) {
    if (activePicker && !activePicker.wrapper.contains(event.target) && !activePicker.menu.contains(event.target)) closePicker(false);
  });
  window.addEventListener('resize', function () { closePicker(false); });
  window.addEventListener('scroll', function (event) {
    if (activePicker && !activePicker.menu.contains(event.target)) closePicker(false);
  }, true);
});