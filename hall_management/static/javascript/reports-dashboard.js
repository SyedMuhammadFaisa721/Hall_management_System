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
  const getChartTheme = function () {
    const light = document.documentElement.dataset.theme === 'light';
    const rootStyle = getComputedStyle(document.documentElement);
    const token = function (name) {
      return rootStyle.getPropertyValue(name).trim();
    };

    return light ? {
      colors: [token('--red'), token('--blue')],
      text: token('--text'),
      muted: token('--muted'),
      surface: token('--surface'),
      border: token('--border-strong'),
      grid: token('--border'),
    } : {
      colors: ['#F87171', '#6EA8FE'],
      text: '#F4F1EA',
      muted: '#8C959C',
      surface: '#11161A',
      border: 'rgba(225, 197, 142, 0.25)',
      grid: 'rgba(255, 255, 255, 0.07)',
    };
  };
  const initialTheme = getChartTheme();

  const chart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: chartData.labels,
      datasets: chartData.datasets.map(function (dataset, index) {
        return {
          ...dataset,
          borderColor: initialTheme.colors[index],
          backgroundColor: initialTheme.colors[index],
          pointBackgroundColor: initialTheme.colors[index],
          pointBorderColor: initialTheme.surface,
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
            color: initialTheme.text,
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
          backgroundColor: initialTheme.surface,
          borderColor: initialTheme.border,
          borderWidth: 1,
          titleColor: initialTheme.text,
          bodyColor: initialTheme.muted,
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
            color: initialTheme.muted,
            minRotation: 45,
            maxRotation: 45,
            autoSkip: false,
            font: { family: 'DM Sans, sans-serif', size: 9 },
          },
        },
        y: {
          beginAtZero: true,
          border: { display: false },
          grid: { color: initialTheme.grid, drawTicks: false },
          ticks: {
            color: initialTheme.muted,
            precision: 0,
            padding: 9,
            font: { family: 'DM Sans, sans-serif', size: 9 },
          },
          title: {
            display: true,
            text: 'Events / bookings',
            color: initialTheme.muted,
            font: { family: 'DM Sans, sans-serif', size: 9 },
          },
        },
      },
    },
  });

  window.addEventListener('hallmaster:themechange', function () {
    const theme = getChartTheme();
    chart.data.datasets.forEach(function (dataset, index) {
      dataset.borderColor = theme.colors[index];
      dataset.backgroundColor = theme.colors[index];
      dataset.pointBackgroundColor = theme.colors[index];
      dataset.pointBorderColor = theme.surface;
    });
    chart.options.plugins.legend.labels.color = theme.text;
    chart.options.plugins.tooltip.backgroundColor = theme.surface;
    chart.options.plugins.tooltip.borderColor = theme.border;
    chart.options.plugins.tooltip.titleColor = theme.text;
    chart.options.plugins.tooltip.bodyColor = theme.muted;
    chart.options.scales.x.ticks.color = theme.muted;
    chart.options.scales.y.grid.color = theme.grid;
    chart.options.scales.y.ticks.color = theme.muted;
    chart.options.scales.y.title.color = theme.muted;
    chart.update('none');
  });
});
