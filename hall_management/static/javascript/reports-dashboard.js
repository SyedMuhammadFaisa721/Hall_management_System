document.addEventListener('DOMContentLoaded', function () {
  const canvas = document.getElementById('booking-comparison-chart');
  const dataElement = document.getElementById('booking-chart-data');
  const errorMessage = document.getElementById('booking-chart-error');

  if (!canvas || !dataElement || !errorMessage) {
    console.error('Booking comparison chart is missing required markup.');
    return;
  }

  if (typeof Chart === 'undefined') {
    errorMessage.hidden = false;
    console.error('Chart.js could not be loaded for the booking comparison chart.');
    return;
  }

  const chartData = JSON.parse(dataElement.textContent);
  const colors = ['#F87171', '#6EA8FE'];

  new Chart(canvas, {
    type: 'line',
    data: {
      labels: chartData.labels,
      datasets: chartData.datasets.map(function (dataset, index) {
        return {
          ...dataset,
          borderColor: colors[index],
          backgroundColor: colors[index],
          pointBackgroundColor: colors[index],
          pointBorderColor: '#11161A',
          pointBorderWidth: 2,
          pointRadius: 3.5,
          pointHoverRadius: 6,
          pointHitRadius: 14,
          borderWidth: 2.5,
          tension: 0.3,
          cubicInterpolationMode: 'monotone',
          spanGaps: false,
          fill: false,
        };
      }),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      layout: {
        padding: { top: 8, right: 12, bottom: 0, left: 4 },
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          align: 'center',
          labels: {
            color: '#F4F1EA',
            usePointStyle: true,
            pointStyle: 'circle',
            boxWidth: 8,
            boxHeight: 8,
            padding: 16,
            font: { family: 'DM Sans, sans-serif', size: 10 },
          },
        },
        tooltip: {
          enabled: true,
          backgroundColor: 'rgba(14, 18, 22, 0.96)',
          borderColor: 'rgba(225, 197, 142, 0.25)',
          borderWidth: 1,
          titleColor: '#F4F1EA',
          bodyColor: '#C6CBD0',
          padding: 11,
          displayColors: true,
          titleFont: { family: 'DM Sans, sans-serif', size: 11, weight: '600' },
          bodyFont: { family: 'DM Sans, sans-serif', size: 10 },
          callbacks: {
            title: function (items) {
              return items[0].label;
            },
            label: function (context) {
              return context.dataset.label + ': ' + context.formattedValue;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: {
            color: '#8C959C',
            minRotation: 45,
            maxRotation: 45,
            autoSkip: false,
            font: { family: 'DM Sans, sans-serif', size: 9 },
          },
        },
        y: {
          beginAtZero: true,
          border: { display: false },
          grid: { color: 'rgba(255, 255, 255, 0.07)', drawTicks: false },
          ticks: {
            color: '#8C959C',
            precision: 0,
            padding: 9,
            font: { family: 'DM Sans, sans-serif', size: 9 },
          },
          title: {
            display: true,
            text: 'Events / bookings',
            color: '#8C959C',
            font: { family: 'DM Sans, sans-serif', size: 9 },
          },
        },
      },
    },
  });
});
