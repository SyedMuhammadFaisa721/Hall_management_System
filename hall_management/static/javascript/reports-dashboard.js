document.addEventListener('DOMContentLoaded', function () {
  const pdfExportButton = document.querySelector('[data-report-export="PDF"]');
  const pdfExportError = document.getElementById('report-export-error');
  if (pdfExportButton && pdfExportError) {
    pdfExportButton.addEventListener('click', async function () {
      if (typeof window.html2pdf !== 'function') {
        pdfExportError.textContent = 'PDF export could not load. Check your connection and try again.';
        pdfExportError.hidden = false;
        console.error('PDF export library is unavailable.');
        return;
      }

      const report = document.getElementById('hallmaster-reports');
      if (!report) {
        pdfExportError.textContent = 'The report could not be found. Refresh the page and try again.';
        pdfExportError.hidden = false;
        console.error('PDF export could not find the report content.');
        return;
      }

      const pdfExportLabel = pdfExportButton.querySelector('span');
      const originalLabel = pdfExportLabel ? pdfExportLabel.textContent : 'Export PDF';
      pdfExportButton.disabled = true;
      pdfExportButton.setAttribute('aria-busy', 'true');
      if (pdfExportLabel) pdfExportLabel.textContent = 'Generating PDF...';
      pdfExportError.hidden = true;

      const exportRoot = document.createElement('div');
      exportRoot.className = 'report-pdf-render-root';
      const exportReport = report.cloneNode(true);
      exportReport.classList.add('report-pdf-export');
      exportReport.querySelector('.report-export-row')?.remove();
      exportReport.querySelector('.report-nav')?.remove();

      report.querySelectorAll('canvas').forEach(function (sourceCanvas) {
        const clonedCanvas = exportReport.querySelector('#' + CSS.escape(sourceCanvas.id));
        if (!clonedCanvas) return;

        const chartImage = document.createElement('img');
        chartImage.className = 'report-pdf-chart-image';
        chartImage.src = sourceCanvas.toDataURL('image/png');
        chartImage.alt = sourceCanvas.getAttribute('aria-label') || 'Report chart';
        chartImage.width = sourceCanvas.width;
        chartImage.height = sourceCanvas.height;
        clonedCanvas.replaceWith(chartImage);
      });

      report.querySelectorAll('.report-donut').forEach(function (sourceDonut, index) {
        const clonedDonut = exportReport.querySelectorAll('.report-donut')[index];
        if (!clonedDonut) return;

        const size = Math.max(1, Math.round(sourceDonut.getBoundingClientRect().width));
        const scale = 2;
        const donutCanvas = document.createElement('canvas');
        donutCanvas.width = size * scale;
        donutCanvas.height = size * scale;
        const context = donutCanvas.getContext('2d');
        const center = donutCanvas.width / 2;
        const lineWidth = donutCanvas.width * 0.19;
        const radius = center - lineWidth / 2;
        const rows = sourceDonut.parentElement.querySelectorAll('.report-legend-row');
        const segments = Array.from(rows).map(function (row) {
          const percentage = row.querySelectorAll('b');
          const value = Number.parseFloat(
            row.dataset.share || (percentage.length ? percentage[percentage.length - 1].textContent : '0'),
          );
          const swatch = row.querySelector('i');
          return {
            value: Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : 0,
            color: swatch ? getComputedStyle(swatch).backgroundColor : '#8299bd',
          };
        }).filter(function (segment) {
          return segment.value > 0;
        });

        context.lineWidth = lineWidth;
        context.lineCap = 'butt';
        context.strokeStyle = '#d7dee5';
        context.beginPath();
        context.arc(center, center, radius, 0, 2 * Math.PI);
        context.stroke();

        let startAngle = -Math.PI / 2;
        segments.forEach(function (segment) {
          const endAngle = startAngle + 2 * Math.PI * segment.value / 100;
          context.strokeStyle = segment.color;
          context.beginPath();
          context.arc(center, center, radius, startAngle, endAngle);
          context.stroke();
          startAngle = endAngle;
        });

        const donutImage = document.createElement('img');
        donutImage.className = 'report-pdf-donut-image';
        donutImage.src = donutCanvas.toDataURL('image/png');
        donutImage.alt = sourceDonut.getAttribute('aria-label') || 'Booking status chart';
        donutImage.width = size;
        donutImage.height = size;

        const centerLabel = clonedDonut.querySelector('.report-donut-center');
        clonedDonut.replaceChildren(donutImage);
        if (centerLabel) clonedDonut.append(centerLabel);
      });

      const exportStyles = document.createElement('style');
      exportStyles.textContent = `
        #hallmaster-reports.report-pdf-export {
          width: 1120px !important; max-width: none !important; margin: 0 !important;
          padding: 28px !important; background: #fff !important; color: #202a33 !important;
          font-family: Arial, sans-serif !important;
        }
        #hallmaster-reports.report-pdf-export * { box-sizing: border-box !important; }
        #hallmaster-reports.report-pdf-export,
        #hallmaster-reports.report-pdf-export .report-section,
        #hallmaster-reports.report-pdf-export .report-card,
        #hallmaster-reports.report-pdf-export .report-kpi,
        #hallmaster-reports.report-pdf-export .report-method,
        #hallmaster-reports.report-pdf-export .report-hall-stat,
        #hallmaster-reports.report-pdf-export .report-staff-summary div,
        #hallmaster-reports.report-pdf-export .report-summary-item,
        #hallmaster-reports.report-pdf-export .report-customer-summary div {
          background: #fff !important; box-shadow: none !important; border-color: #d7dee5 !important;
        }
        #hallmaster-reports.report-pdf-export * { color: #26333d !important; }
        #hallmaster-reports.report-pdf-export .report-heading h1,
        #hallmaster-reports.report-pdf-export .report-section-heading h2,
        #hallmaster-reports.report-pdf-export .report-card-heading h3,
        #hallmaster-reports.report-pdf-export .report-kpi-value,
        #hallmaster-reports.report-pdf-export .report-staff-summary strong,
        #hallmaster-reports.report-pdf-export table strong { color: #17212a !important; }
        #hallmaster-reports.report-pdf-export .report-heading .eyebrow,
        #hallmaster-reports.report-pdf-export .report-kpi-foot,
        #hallmaster-reports.report-pdf-export .report-kpi-icon { color: #8a6633 !important; }
        #hallmaster-reports.report-pdf-export .report-donut::before { background: #fff !important; }
        #hallmaster-reports.report-pdf-export .report-donut { background: none !important; }
        #hallmaster-reports.report-pdf-export .report-donut::before { display: none !important; }
        #hallmaster-reports.report-pdf-export .report-pdf-donut-image {
          position: absolute; inset: 0; width: 100%; height: 100%;
        }
        #hallmaster-reports.report-pdf-export .report-pdf-chart-image {
          display: block; width: 100%; height: 100%; object-fit: contain;
        }
        #hallmaster-reports.report-pdf-export .report-table-scroll { overflow: visible !important; }
        #hallmaster-reports.report-pdf-export .report-hall-table,
        #hallmaster-reports.report-pdf-export .report-customer-table,
        #hallmaster-reports.report-pdf-export .report-staff-table { min-width: 0 !important; }
        #hallmaster-reports.report-pdf-export .report-section,
        #hallmaster-reports.report-pdf-export .report-card,
        #hallmaster-reports.report-pdf-export .report-kpi,
        #hallmaster-reports.report-pdf-export table tr {
          break-inside: avoid !important; page-break-inside: avoid !important;
        }
      `;
      exportReport.prepend(exportStyles);
      exportRoot.append(exportReport);
      document.body.append(exportRoot);

      try {
        await window.html2pdf().set({
          margin: [8, 8, 10, 8],
          filename: 'hallmaster-report-' + new Date().toISOString().slice(0, 10) + '.pdf',
          image: { type: 'jpeg', quality: 0.96 },
          html2canvas: {
            scale: 2,
            backgroundColor: '#ffffff',
            windowWidth: 1160,
            scrollX: 0,
            scrollY: 0,
            useCORS: true,
          },
          jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' },
          pagebreak: { mode: ['css', 'legacy'], avoid: ['.report-kpi', 'table tr'] },
        }).from(exportReport).save();
      } catch (error) {
        pdfExportError.textContent = 'PDF export failed. Please try again.';
        pdfExportError.hidden = false;
        console.error('Unable to generate the report PDF.', error);
      } finally {
        exportRoot.remove();
        pdfExportButton.disabled = false;
        pdfExportButton.removeAttribute('aria-busy');
        if (pdfExportLabel) pdfExportLabel.textContent = originalLabel;
      }
    });
  }

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
