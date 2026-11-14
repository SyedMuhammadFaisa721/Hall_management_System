document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#booking-form");
  const selects = document.querySelectorAll(".booking-form-field select");
  let activeDropdown = null;

  function closeDropdown(returnFocus = false) {
    if (!activeDropdown) return;

    const { trigger, menu } = activeDropdown;
    menu.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    activeDropdown = null;

    if (returnFocus) trigger.focus();
  }

  function focusOption(menu, index) {
    const options = [...menu.querySelectorAll('[role="option"]')];
    if (!options.length) return;

    const nextIndex = Math.max(0, Math.min(index, options.length - 1));
    options[nextIndex].focus();
  }

  selects.forEach((select, selectIndex) => {
    const field = select.closest(".booking-form-field");
    const label = field.querySelector("label");
    const menuId = `booking-select-menu-${selectIndex}`;
    const triggerId = `booking-select-trigger-${selectIndex}`;
    const trigger = document.createElement("button");
    const menu = document.createElement("div");

    trigger.type = "button";
    trigger.id = triggerId;
    trigger.className = "booking-select-trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    trigger.setAttribute("aria-controls", menuId);
    trigger.setAttribute("aria-label", label.textContent.trim());

    menu.id = menuId;
    menu.className = "booking-select-menu";
    menu.setAttribute("role", "listbox");
    menu.setAttribute("aria-label", label.textContent.trim());
    menu.hidden = true;

    [...select.options].forEach((option, optionIndex) => {
      const menuOption = document.createElement("div");
      menuOption.className = "booking-select-option";
      menuOption.id = `${menuId}-option-${optionIndex}`;
      menuOption.setAttribute("role", "option");
      menuOption.setAttribute("aria-selected", String(optionIndex === select.selectedIndex));
      menuOption.tabIndex = -1;
      menuOption.textContent = option.textContent.trim();
      menuOption.addEventListener("click", () => {
        select.selectedIndex = optionIndex;
        select.dispatchEvent(new Event("input", { bubbles: true }));
        select.dispatchEvent(new Event("change", { bubbles: true }));
        syncSelection();
        closeDropdown(true);
      });
      menu.append(menuOption);
    });

    function syncSelection() {
      const selectedOption = select.options[select.selectedIndex];
      trigger.textContent = selectedOption ? selectedOption.textContent.trim() : "Choose an option";
      trigger.setAttribute("aria-label", `${label.textContent.trim()}: ${trigger.textContent}`);
      menu.querySelectorAll('[role="option"]').forEach((option, optionIndex) => {
        option.setAttribute("aria-selected", String(optionIndex === select.selectedIndex));
      });
    }

    function positionMenu() {
      const bounds = trigger.getBoundingClientRect();
      const menuHeight = menu.offsetHeight;
      const gap = 7;
      const openAbove = window.innerHeight - bounds.bottom < menuHeight + gap && bounds.top > menuHeight + gap;
      const top = openAbove ? bounds.top - menuHeight - gap : bounds.bottom + gap;
      const left = Math.max(10, Math.min(bounds.left, window.innerWidth - bounds.width - 10));

      menu.style.top = `${top}px`;
      menu.style.left = `${left}px`;
      menu.style.width = `${bounds.width}px`;
    }

    function openMenu() {
      closeDropdown();
      menu.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      activeDropdown = { trigger, menu };
      positionMenu();
      focusOption(menu, select.selectedIndex);
    }

    trigger.addEventListener("click", () => {
      if (activeDropdown?.trigger === trigger) {
        closeDropdown();
      } else {
        openMenu();
      }
    });

    trigger.addEventListener("keydown", event => {
      if (["ArrowDown", "ArrowUp"].includes(event.key)) {
        event.preventDefault();
        openMenu();
      }
    });

    menu.addEventListener("keydown", event => {
      const options = [...menu.querySelectorAll('[role="option"]')];
      const currentIndex = options.indexOf(document.activeElement);

      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        focusOption(menu, currentIndex + (event.key === "ArrowDown" ? 1 : -1));
      } else if (event.key === "Home" || event.key === "End") {
        event.preventDefault();
        focusOption(menu, event.key === "Home" ? 0 : options.length - 1);
      } else if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        document.activeElement.click();
      } else if (event.key === "Escape") {
        event.preventDefault();
        closeDropdown(true);
      } else if (event.key === "Tab") {
        closeDropdown();
      }
    });

    select.classList.add("booking-form-native");
    select.setAttribute("aria-hidden", "true");
    select.tabIndex = -1;
    select.after(trigger);
    document.body.append(menu);
    select.addEventListener("change", syncSelection);
    select.form?.addEventListener("reset", () => window.setTimeout(syncSelection));
    syncSelection();
  });

  document.addEventListener("pointerdown", event => {
    if (!activeDropdown) return;
    if (!activeDropdown.trigger.contains(event.target) && !activeDropdown.menu.contains(event.target)) {
      closeDropdown();
    }
  });

  window.addEventListener("resize", () => closeDropdown());
  window.addEventListener("scroll", () => closeDropdown());

  const summary = {
    customer: document.querySelector("#booking-summary-customer"),
    event: document.querySelector("#booking-summary-event"),
    date: document.querySelector("#booking-summary-date"),
    halls: document.querySelector("#booking-summary-halls"),
    service: document.querySelector("#booking-summary-service"),
    method: document.querySelector("#booking-summary-method"),
    guests: document.querySelector("#booking-summary-guests"),
    price: document.querySelector("#booking-summary-price"),
    status: document.querySelector("#booking-summary-status"),
  };

  function updateSummary() {
    const customerName = form.elements.customer_name.value.trim();
    const eventName = form.elements.event_name.value.trim();
    const eventDate = form.elements.event_date.value;
    const hallNames = [...form.querySelectorAll('input[name="event_hall"]:checked')]
      .map(input => input.closest("label").textContent.trim())
      .join(", ");
    const price = form.elements.hall_price.value;
    const status = form.querySelector('input[name="status"]:checked');
    const service = form.querySelector('input[name="service"]:checked');
    const method = form.querySelector('input[name="method"]:checked');

    summary.customer.textContent = customerName || "Add customer name";
    summary.event.textContent = eventName || "Add event name";
    summary.date.textContent = eventDate
      ? new Date(`${eventDate}T00:00:00`).toLocaleDateString(undefined, {
        day: "2-digit",
        month: "short",
        year: "numeric",
      })
      : "Choose a date";
    summary.halls.textContent = hallNames || "Select a hall";
    summary.service.textContent = service ? service.value : "Choose service";
    summary.method.textContent = method ? method.closest("label").textContent.trim() : "Choose method";
    summary.guests.textContent = form.elements.event_guest.value || "—";
    summary.price.textContent = Number(price || 0).toLocaleString();
    summary.status.textContent = status ? status.value : "Pending";
  }

  form.addEventListener("input", updateSummary);
  form.addEventListener("change", updateSummary);
  updateSummary();
});