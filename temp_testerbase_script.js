

    (() => {

        const report = document.querySelector('.reports-page');

        if (!report) return;



        const periodLabels = { today: 'Today', week: 'This week', month: 'This month', quarter: 'This quarter', year: 'This year' };

        const sampleMetrics = {

            today:   { revenue: 'Rs 42.5K', bookings: '2', collected: 'Rs 31K', payments: '2', expenses: 'Rs 8.2K', profit: 'Rs 34.3K' },

            week:    { revenue: 'Rs 286K', bookings: '9', collected: 'Rs 214K', payments: '8', expenses: 'Rs 76K', profit: 'Rs 210K' },

            month:   { revenue: 'Rs 1.24M', bookings: '24', collected: 'Rs 980K', payments: '21', expenses: 'Rs 386K', profit: 'Rs 854K' },

            quarter: { revenue: 'Rs 4.18M', bookings: '76', collected: 'Rs 3.31M', payments: '68', expenses: 'Rs 1.29M', profit: 'Rs 2.89M' },

            year:    { revenue: 'Rs 15.75M', bookings: '284', collected: 'Rs 12.40M', payments: '246', expenses: 'Rs 4.82M', profit: 'Rs 10.93M' }

        };

        const chartSamples = {

            today: { labels: ['AM', 'PM'], revenue: [38, 64], expenses: [20, 28] },

            week: { labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], revenue: [35, 48, 42, 67, 55, 88, 72], expenses: [20, 28, 24, 32, 26, 40, 35] },

            month: { labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'], revenue: [44, 70, 58, 92], expenses: [25, 38, 30, 46] },

            quarter: { labels: ['Month 1', 'Month 2', 'Month 3'], revenue: [52, 74, 92], expenses: [32, 40, 46] },

            year: { labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], revenue: [55, 63, 69, 61, 77, 82, 73, 87, 92, 84, 96, 100], expenses: [25, 29, 33, 30, 38, 42, 36, 46, 49, 43, 54, 58] }

        };



        const formatDate = date => date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });

        const getRange = period => {

            const today = new Date();

            today.setHours(0, 0, 0, 0);

            const start = new Date(today);

            const end = new Date(today);

            if (period === 'week') {

                start.setDate(today.getDate() - ((today.getDay() + 6) % 7));

                end.setDate(start.getDate() + 6);

            } else if (period === 'month') {

                start.setDate(1);

                end.setMonth(end.getMonth() + 1, 0);

            } else if (period === 'quarter') {

                const quarterMonth = Math.floor(today.getMonth() / 3) * 3;

                start.setMonth(quarterMonth, 1);

                end.setMonth(quarterMonth + 3, 0);

            } else if (period === 'year') {

                start.setMonth(0, 1);

                end.setMonth(11, 31);

            }

            return period === 'today' ? formatDate(today) : `${formatDate(start)} - ${formatDate(end)}`;

        };



        report.querySelectorAll('[data-period]').forEach(button => {

            button.addEventListener('click', () => {

                const period = button.dataset.period;

                report.querySelectorAll('[data-period]').forEach(tab => {

                    const selected = tab === button;

                    tab.classList.toggle('active', selected);

                    tab.setAttribute('aria-pressed', String(selected));

                });

                report.querySelector('#rp-period-label').textContent = getRange(period);

                const sample = chartSamples[period];

                const revenueBars = report.querySelector('#rp-revenue-bars');

                const expenseBars = report.querySelector('#rp-expense-bars');

                const barLabels = report.querySelector('#rp-bar-labels');

                revenueBars.replaceChildren();

                expenseBars.replaceChildren();

                barLabels.replaceChildren();

                const plotLeft = 45, plotWidth = 620, plotBottom = 205, plotHeight = 180;

                const slot = plotWidth / sample.labels.length;

                const revenueWidth = Math.min(22, slot * .42);

                const expenseWidth = Math.min(10, slot * .2);

                sample.labels.forEach((label, index) => {

                    const center = plotLeft + slot * (index + .5);

                    const revenueHeight = plotHeight * sample.revenue[index] / 100;

                    const expenseHeight = plotHeight * sample.expenses[index] / 100;

                    const revenueBar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');

                    revenueBar.setAttribute('class', 'rp-bar');

                    revenueBar.setAttribute('x', center - revenueWidth / 2 - expenseWidth / 2);

                    revenueBar.setAttribute('y', plotBottom - revenueHeight);

                    revenueBar.setAttribute('width', revenueWidth);

                    revenueBar.setAttribute('height', revenueHeight);

                    revenueBars.append(revenueBar);

                    const expenseBar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');

                    expenseBar.setAttribute('class', 'rp-bar');

                    expenseBar.setAttribute('x', center + revenueWidth / 2 - expenseWidth / 2);

                    expenseBar.setAttribute('y', plotBottom - expenseHeight);

                    expenseBar.setAttribute('width', expenseWidth);

                    expenseBar.setAttribute('height', expenseHeight);

                    expenseBars.append(expenseBar);

                    if (sample.labels.length <= 7 || index % 2 === 0) {

                        const axisLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');

                        axisLabel.setAttribute('class', 'rp-axis');

                        axisLabel.setAttribute('x', center - 10);

                        axisLabel.setAttribute('y', '222');

                        axisLabel.textContent = label;

                        barLabels.append(axisLabel);

                    }

                });

                Object.entries(sampleMetrics[period]).forEach(([key, value]) => {

                    const metric = report.querySelector(`[data-metric="${key}"]`);

                    if (metric) metric.textContent = value;

                });

                report.querySelectorAll('.rp-chip').forEach(chip => {

                    if (['This year', '284 total', '284 events'].includes(chip.textContent.trim())) {

                        chip.textContent = periodLabels[period];

                    }

                });

                report.querySelectorAll('.rp-card-head p').forEach(caption => {

                    if (caption.dataset.baseCaption === undefined) caption.dataset.baseCaption = caption.textContent;

                    if (caption.textContent.includes('across the year')) caption.textContent = `Revenue and expenses · ${periodLabels[period].toLowerCase()}`;

                    if (caption.textContent.includes('Monthly event volume')) caption.textContent = `Event volume · ${periodLabels[period].toLowerCase()}`;

                });

            });

        });

        report.querySelector('[data-period="year"]').click();

    })();


