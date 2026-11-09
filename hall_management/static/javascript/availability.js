document.addEventListener('DOMContentLoaded', function () {
  const calendarElement = document.getElementById('availability-calendar');
  if (!calendarElement) return;

  if (!window.FullCalendar) {
    console.error('FullCalendar failed to load; the availability calendar was not initialized.');
    return;
  }

  const monthTitle = document.getElementById('availability-calendar-title');
  const selectedDateTitle = document.getElementById('selected-date-title');
  const statusElement = document.getElementById('selected-event-status');
  const eventTitle = document.getElementById('selected-event-title');
  const eventCopy = document.getElementById('selected-event-copy');
  const eventLink = document.getElementById('selected-event-link');
  const eventCount = document.getElementById('selected-event-count');
  const hallsInUse = document.getElementById('selected-halls-in-use');
  const hallsFree = document.getElementById('selected-halls-free');
  const errorElement = document.getElementById('availability-calendar-error');
  const portions = JSON.parse(document.getElementById('availability-portions-data').textContent);
  const bookingsByDate = new Map();
  let selectedDate = toDateKey(new Date());

  function toDateKey(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function parseDateKey(dateKey) {
    const parts = dateKey.split('-').map(Number);
    return new Date(parts[0], parts[1] - 1, parts[2], 12);
  }

  function updateSelectedCell() {
    calendarElement.querySelectorAll('.fc-daygrid-day[data-date]').forEach(function (cell) {
      cell.classList.toggle('calendar-selected-date', cell.dataset.date === selectedDate);
    });
  }

  function updateWeekdayColors(theme) {
    const isLightTheme = theme === 'light';
    const textColor = isLightTheme ? '#000000' : '#ffffff';
    const headerColor = isLightTheme ? '#ffffff' : '#101418';
    calendarElement.querySelectorAll('.fc-col-header-cell').forEach(function (cell) {
      cell.style.setProperty('background-color', headerColor, 'important');
      const label = cell.querySelector('.fc-col-header-cell-cushion');
      if (label) label.style.setProperty('color', textColor, 'important');
    });
  }

  function createDayCellContent(info) {
    const content = document.createElement('div');
    content.className = 'availability-day-content';

    const dayNumber = document.createElement('span');
    dayNumber.className = 'availability-day-number';
    dayNumber.textContent = String(info.date.getDate());
    content.append(dayNumber);

    const portionsList = document.createElement('div');
    portionsList.className = 'availability-portions';
    portions.forEach(function (portion) {
      const row = document.createElement('div');
      row.className = 'availability-portion';
      row.dataset.portionId = String(portion.id);

      const name = document.createElement('span');
      name.className = 'availability-portion-name';
      name.dataset.short = portion.portion_name;
      name.textContent = `Portion ${portion.portion_name}`;

      const status = document.createElement('span');
      status.className = 'availability-portion-status';
      status.textContent = 'Free';

      row.append(name, status);
      portionsList.append(row);
    });
    content.append(portionsList);
    return { domNodes: [content] };
  }

  function updatePortionStatusesForCell(cell) {
    const dateBookings = bookingsByDate.get(cell.dataset.date) || [];
    const bookedPortions = new Set();
    dateBookings.forEach(function (booking) {
      if (!booking.extendedProps.isCancelled) {
        booking.extendedProps.halls.forEach(function (hall) {
          bookedPortions.add(String(hall.id));
        });
      }
    });

    cell.querySelectorAll('.availability-portion').forEach(function (row) {
      const isBooked = bookedPortions.has(row.dataset.portionId);
      row.classList.toggle('is-booked', isBooked);
      const status = row.querySelector('.availability-portion-status');
      status.textContent = isBooked ? 'Booked' : 'Free';
      status.classList.toggle('is-booked', isBooked);
    });
  }

  function updatePortionStatuses() {
    calendarElement.querySelectorAll('.fc-daygrid-day[data-date]').forEach(updatePortionStatusesForCell);
  }

  function appendDetail(container, label, value) {
    const row = document.createElement('div');
    row.className = 'selected-booking-detail';
    const labelElement = document.createElement('strong');
    labelElement.textContent = `${label}:`;
    const valueElement = document.createElement('span');
    valueElement.textContent = value || '—';
    row.append(labelElement, valueElement);
    container.append(row);
  }

  function updateSelectedDate(dateKey, calendar) {
    selectedDate = dateKey;
    const date = parseDateKey(dateKey);
    const bookings = calendar.getEvents().filter(function (event) {
      return event.start && toDateKey(event.start) === dateKey;
    });
    const dateLabel = new Intl.DateTimeFormat('en', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    }).format(date);
    const usedPortions = new Set();

    bookings.forEach(function (booking) {
      if (!booking.extendedProps.isCancelled) {
        booking.extendedProps.halls.forEach(function (hall) {
          usedPortions.add(String(hall.id));
        });
      }
    });

    selectedDateTitle.textContent = dateLabel;
    eventCount.textContent = String(bookings.length);
    hallsInUse.textContent = String(usedPortions.size);
    hallsFree.textContent = String(Math.max(0, portions.length - usedPortions.size));
    statusElement.hidden = true;
    eventCopy.replaceChildren();

    if (!bookings.length) {
      eventTitle.textContent = 'No events scheduled';
      eventCopy.textContent = 'This date is currently available.';
      eventLink.hidden = true;
    } else {
      eventTitle.textContent = `${bookings.length} booking${bookings.length === 1 ? '' : 's'} scheduled`;
      eventLink.hidden = false;

      bookings.forEach(function (booking) {
        const details = booking.extendedProps;
        const card = document.createElement('article');
        card.className = 'selected-booking-card';

        const heading = document.createElement('div');
        heading.className = 'selected-booking-heading';
        const name = document.createElement('strong');
        name.textContent = booking.title;
        const status = document.createElement('span');
        const normalizedStatus = details.status.toLowerCase();
        const statusClass = details.isCancelled
          ? 'cancelled'
          : normalizedStatus.includes('pending') ? 'pending' : 'confirmed';
        status.className = `status ${statusClass}`;
        status.textContent = details.status;
        heading.append(name, status);
        card.append(heading);

        appendDetail(card, 'Booking ID', details.bookingId);
        appendDetail(card, 'Customer', details.customerName);
        appendDetail(card, 'Portions', details.halls.map(function (hall) {
          return `Portion ${hall.name}`;
        }).join(', '));
        appendDetail(card, 'Guests', String(details.guestCount));
        appendDetail(card, 'Time', details.eventTime);
        appendDetail(card, 'Hall price', `Rs ${details.hallPrice}`);
        appendDetail(card, 'Special request', details.specialRequest);
        eventCopy.append(card);
      });
    }

    updateSelectedCell();
  }

  const calendar = new FullCalendar.Calendar(calendarElement, {
    initialView: 'dayGridMonth',
    initialDate: selectedDate,
    firstDay: 0,
    fixedWeekCount: true,
    showNonCurrentDates: true,
    headerToolbar: false,
    height: 'auto',
    dayCellContent: createDayCellContent,
    dayCellDidMount: function (info) {
      updatePortionStatusesForCell(info.el);
    },
    events: function (fetchInfo, successCallback, failureCallback) {
      const eventsUrl = new URL(calendarElement.dataset.eventsUrl, window.location.origin);
      eventsUrl.searchParams.set('start', fetchInfo.startStr.slice(0, 10));
      eventsUrl.searchParams.set('end', fetchInfo.endStr.slice(0, 10));

      fetch(eventsUrl, { headers: { Accept: 'application/json' } })
        .then(function (response) {
          if (!response.ok) {
            return response.json().then(function (data) {
              throw new Error(data.error || `Calendar request failed (${response.status}).`);
            });
          }
          return response.json();
        })
        .then(function (data) {
          if (!Array.isArray(data.events)) {
            throw new Error('The calendar response did not contain booking events.');
          }
          bookingsByDate.clear();
          data.events.forEach(function (event) {
            const dayBookings = bookingsByDate.get(event.start) || [];
            dayBookings.push(event);
            bookingsByDate.set(event.start, dayBookings);
          });
          errorElement.hidden = true;
          successCallback(data.events);
          updatePortionStatuses();
          window.requestAnimationFrame(function () {
            updateSelectedDate(selectedDate, calendar);
          });
        })
        .catch(function (error) {
          console.error('Unable to load availability bookings.', error);
          errorElement.textContent = 'Bookings could not be loaded. Please try changing the month or reload the page.';
          errorElement.hidden = false;
          failureCallback(error);
        });
    },
    eventDisplay: 'block',
    dayMaxEvents: 2,
    datesSet: function (info) {
      monthTitle.textContent = info.view.title;
      updateSelectedCell();
      updatePortionStatuses();
    },
    dateClick: function (info) {
      updateSelectedDate(info.dateStr, calendar);
    },
    eventClick: function (info) {
      info.jsEvent.preventDefault();
      updateSelectedDate(toDateKey(info.event.start), calendar);
    },
    eventClassNames: function (info) {
      const status = info.event.extendedProps.status.toLowerCase();
      const classNames = ['day-booking'];
      if (status.includes('pending')) classNames.push('pending');
      if (info.event.extendedProps.isCancelled) classNames.push('blocked');
      return classNames;
    },
  });

  calendarElement.addEventListener('click', function (event) {
    if (event.target.closest('.fc-daygrid-more-link')) {
      window.requestAnimationFrame(updatePortionStatuses);
    }
  });

  document.getElementById('calendar-prev').addEventListener('click', function () {
    calendar.prev();
  });
  document.getElementById('calendar-next').addEventListener('click', function () {
    calendar.next();
  });
  document.getElementById('calendar-today').addEventListener('click', function () {
    calendar.today();
    updateSelectedDate(toDateKey(calendar.getDate()), calendar);
  });

  calendar.render();
  updateWeekdayColors(document.documentElement.dataset.theme);
  window.addEventListener('hallmaster:themechange', function (event) {
    updateWeekdayColors(event.detail.theme);
  });
  updateSelectedDate(selectedDate, calendar);
});
