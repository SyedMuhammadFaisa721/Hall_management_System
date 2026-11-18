document.addEventListener("DOMContentLoaded", () => {
  const bookingSelect = document.querySelector("#id_booking");
  const amountInput = document.querySelector("#id_amount");
  const dataElement = document.querySelector("#payment-booking-details");
  const summaryTitle = document.querySelector("#booking-summary-title");
  const summaryPlaceholder = document.querySelector("#booking-summary-placeholder");
  const summaryFields = document.querySelector("#booking-summary-fields");

  if (!bookingSelect || !amountInput || !dataElement || !summaryTitle || !summaryPlaceholder || !summaryFields) {
    return;
  }

  const bookings = JSON.parse(dataElement.textContent);
  const formatMoney = (amount) => `PKR ${Number(amount).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

  function updateBookingSummary() {
    const booking = bookings[bookingSelect.value];
    amountInput.setCustomValidity("");

    if (!booking) {
      summaryTitle.textContent = "Choose a booking";
      summaryPlaceholder.hidden = false;
      summaryFields.hidden = true;
      amountInput.removeAttribute("max");
      return;
    }

    summaryTitle.textContent = booking.customer_name;
    summaryPlaceholder.hidden = true;
    summaryFields.hidden = false;

    const values = {
      ...booking,
      event_type_status: `${booking.event_type} · ${booking.status}`,
      event_schedule: `${booking.event_date} · ${booking.event_time}`,
    };

    summaryFields.querySelectorAll("[data-booking-field]").forEach((field) => {
      const key = field.dataset.bookingField;
      field.textContent = ["hall_price", "advance_amount", "recorded_payment_total", "remaining_balance"].includes(key)
        ? formatMoney(values[key])
        : values[key];
    });

    amountInput.max = booking.remaining_balance;
    validateAmount();
  }

  function validateAmount() {
    const booking = bookings[bookingSelect.value];
    const amount = Number(amountInput.value);
    if (booking && amountInput.value && amount > Number(booking.remaining_balance)) {
      amountInput.setCustomValidity(
        `Amount cannot exceed the remaining balance of ${formatMoney(booking.remaining_balance)}.`,
      );
    } else {
      amountInput.setCustomValidity("");
    }
  }

  bookingSelect.addEventListener("change", updateBookingSummary);
  amountInput.addEventListener("input", validateAmount);
  updateBookingSummary();
});
