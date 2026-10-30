// Dashboard graph drawing code starts here.
const drawDashboardRevenueChart = () => {
    const revenueData = document.getElementById("monthly-revenue-data");
    const monthData = document.getElementById("revenue-chart-months");
    const chartData = document.getElementById("revenue-chart-data");
    if (!revenueData || !monthData || !chartData) return;

    const monthlyRevenue = JSON.parse(revenueData.textContent);
    const chartMonths = JSON.parse(monthData.textContent);
    const chartLeft = 55;
    const chartRight = 710;
    const chartBottom = 180;
    const chartTop = 20;
    const chartWidth = chartRight - chartLeft;
    const chartX = index => chartLeft + (chartWidth * index / 11);

    // Dashboard graph Y-axis scale code starts here.
    const rawMaxRevenue = Math.max(...monthlyRevenue, 0);
    const scalePower = rawMaxRevenue > 0 ? 10 ** Math.floor(Math.log10(rawMaxRevenue)) : 1;
    const scaledMaximum = rawMaxRevenue / scalePower;
    const roundedMaximum = scaledMaximum <= 1 ? 1 : scaledMaximum <= 2 ? 2 : scaledMaximum <= 5 ? 5 : 10;
    const maxRevenue = rawMaxRevenue > 0 ? roundedMaximum * scalePower : 1;
    const formatChartAmount = amount => {
        if (amount >= 10000000) return `Rs ${(amount / 10000000).toFixed(amount >= 100000000 ? 0 : 1)}Cr`;
        if (amount >= 100000) return `Rs ${(amount / 100000).toFixed(amount >= 1000000 ? 0 : 1)}L`;
        if (amount >= 1000) return `Rs ${(amount / 1000).toFixed(amount >= 100000 ? 0 : 1)}K`;
        return `Rs ${Number(amount).toLocaleString("en-PK")}`;
    };
    const chartY = value => chartBottom - ((Number(value) / maxRevenue) * (chartBottom - chartTop));
    const points = monthlyRevenue.map((value, index) => ({
        x: chartX(index),
        y: chartY(value)
    }));

    // Dashboard graph smooth line code starts here.
    const linePath = points.reduce((path, point, index) => {
        if (index === 0) return `M${point.x.toFixed(2)} ${point.y.toFixed(2)}`;
        const previous = points[index - 1];
        const controlX = ((previous.x + point.x) / 2).toFixed(2);
        return `${path} C${controlX} ${previous.y.toFixed(2)}, ${controlX} ${point.y.toFixed(2)}, ${point.x.toFixed(2)} ${point.y.toFixed(2)}`;
    }, "");

    // Dashboard graph SVG elements code starts here.
    const svgNamespace = "http://www.w3.org/2000/svg";
    const createSvgElement = (name, attributes = {}) => {
        const element = document.createElementNS(svgNamespace, name);
        Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
        return element;
    };

    // Dashboard graph Y-axis labels code starts here.
    [0, 0.25, 0.5, 0.75, 1].forEach(ratio => {
        const y = chartBottom - ((chartBottom - chartTop) * ratio);
        const label = createSvgElement("text", {
            class: "chart-label",
            x: "48",
            y: (y + 3).toFixed(2),
            "text-anchor": "end"
        });
        label.textContent = formatChartAmount(maxRevenue * ratio);
        chartData.appendChild(label);
    });

    // Dashboard graph revenue tooltip code starts here.
    chartData.appendChild(createSvgElement("path", {
        class: "chart-area",
        d: `${linePath} L${chartRight} ${chartBottom} L${chartLeft} ${chartBottom} Z`
    }));
    chartData.appendChild(createSvgElement("path", {
        class: "chart-line",
        d: linePath
    }));
    points.forEach((point, index) => {
        const pointElement = createSvgElement("circle", {
            class: "chart-point",
            cx: point.x.toFixed(2),
            cy: point.y.toFixed(2),
            r: "3.4"
        });
        const title = createSvgElement("title");
        title.textContent = `${chartMonths[index]}: Rs ${monthlyRevenue[index].toLocaleString("en-PK")}`;
        pointElement.appendChild(title);
        chartData.appendChild(pointElement);
    });
    chartMonths.forEach((month, index) => {
        const label = createSvgElement("text", {
            class: "chart-label",
            x: chartX(index).toFixed(2),
            y: "200",
            "text-anchor": "middle"
        });
        label.textContent = month;
        chartData.appendChild(label);
    });
};

document.addEventListener("DOMContentLoaded", drawDashboardRevenueChart);
