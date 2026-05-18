// Global chart instances registry
window.chartInstances = {};

window.createChartCard = function(parent, id, title) {
    const card = document.createElement("div");
    card.className = "chart-card glass-card";
    card.innerHTML = `<h3>${title}</h3><div id="${id}"></div>`;
    parent.appendChild(card);
};

window.createRamanCard = function(parent) {
    const card = document.createElement("div");
    card.className = "chart-card glass-card";
    card.style.gridColumn = "1 / -1";
    card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <h3>RAMAN Spectroscopy - ALS Baseline Correction</h3>
            <select id="raman-sample-select" style="padding: 6px 12px; font-size: 13px;"></select>
        </div>
        <div id="raman-chart"></div>
    `;
    parent.appendChild(card);
};

window.renderScreePlot = function(scree) {
    const options = {
        chart: { type: 'bar', height: 320, toolbar: { show: false }, background: 'transparent' },
        theme: { mode: 'dark' },
        series: [{ name: 'Variance Ratio', data: scree.variance.map(v => parseFloat((v * 100).toFixed(2))) }],
        xaxis: { categories: scree.labels },
        colors: ['#00f0ff'],
        yaxis: { title: { text: 'Percentage (%)' } }
    };
    window.chartInstances["scree"] = new ApexCharts(document.getElementById("scree-chart"), options);
    window.chartInstances["scree"].render();
};

window.renderScoresPlot = function(scores, xKey, yKey, xLabel, yLabel) {
    const classes = [...new Set(scores.map(s => s.class))];
    const series = classes.map(cls => ({
        name: `Class ${cls}`,
        data: scores.filter(s => s.class === cls).map(s => ({ x: s[xKey], y: s[yKey], label: s.name }))
    }));

    const options = {
        chart: { type: 'scatter', height: 320, background: 'transparent' },
        theme: { mode: 'dark' },
        series: series,
        xaxis: { title: { text: xLabel }, labels: { formatter: val => parseFloat(val).toFixed(2) } },
        yaxis: { title: { text: yLabel }, labels: { formatter: val => parseFloat(val).toFixed(2) } },
        tooltip: {
            custom: ({ series, seriesIndex, dataPointIndex, w }) => {
                const dataObj = w.config.series[seriesIndex].data[dataPointIndex];
                return `<div class="glass-card" style="padding: 8px; font-size: 11px;">
                    <strong>${dataObj.label}</strong><br>
                    Class: ${w.config.series[seriesIndex].name}<br>
                    X: ${dataObj.x.toFixed(4)}<br>
                    Y: ${dataObj.y.toFixed(4)}
                </div>`;
            }
        }
    };
    window.chartInstances["scores"] = new ApexCharts(document.getElementById("scores-chart"), options);
    window.chartInstances["scores"].render();
};

window.renderLoadingsPlot = function(loadings, keys, names) {
    const series = keys.map((key, i) => ({
        name: names[i],
        data: loadings.wavelengths.map((wl, idx) => ({ x: wl, y: loadings[key][idx] }))
    }));

    const options = {
        chart: { type: 'line', height: 320, background: 'transparent' },
        theme: { mode: 'dark' },
        series: series,
        xaxis: { title: { text: 'Wavelength (nm)' }, labels: { formatter: val => Math.round(val) } },
        stroke: { width: 2 }
    };
    window.chartInstances["loadings"] = new ApexCharts(document.getElementById("loadings-chart"), options);
    window.chartInstances["loadings"].render();
};

window.renderResidualsPlot = function(residuals) {
    const series = [{
        name: 'Samples',
        data: residuals.map(r => ({ x: r.t2, y: r.q, label: r.name }))
    }];

    const options = {
        chart: { type: 'scatter', height: 320, background: 'transparent' },
        theme: { mode: 'dark' },
        series: series,
        xaxis: { title: { text: "Hotelling's T²" } },
        yaxis: { title: { text: 'Q Residual' } },
        colors: ['#ef4444'],
        tooltip: {
            custom: ({ w, seriesIndex, dataPointIndex }) => {
                const item = w.config.series[seriesIndex].data[dataPointIndex];
                return `<div class="glass-card" style="padding: 8px; font-size: 11px;">
                    <strong>${item.label}</strong><br>
                    T²: ${item.x.toFixed(4)}<br>
                    Q: ${item.y.toFixed(4)}
                </div>`;
            }
        }
    };
    window.chartInstances["residuals"] = new ApexCharts(document.getElementById("residuals-chart"), options);
    window.chartInstances["residuals"].render();
};

window.renderRamanSpectra = function(plots) {
    const select = document.getElementById("raman-sample-select");
    select.innerHTML = "";
    
    plots.samples.forEach((sample, i) => {
        const opt = document.createElement("option");
        opt.value = i;
        opt.textContent = sample.name;
        select.appendChild(opt);
    });

    const updateRamanChart = (idx) => {
        const sample = plots.samples[idx];
        const series = [
            { name: "Raw Signal", data: plots.wavelengths.map((wl, i) => ({ x: wl, y: sample.raw[i] })) },
            { name: "ALS Baseline", data: plots.wavelengths.map((wl, i) => ({ x: wl, y: sample.baseline[i] })) },
            { name: "Corrected Raman", data: plots.wavelengths.map((wl, i) => ({ x: wl, y: sample.corrected[i] })) }
        ];

        const options = {
            chart: { type: 'line', height: 400, background: 'transparent' },
            theme: { mode: 'dark' },
            series: series,
            xaxis: { title: { text: 'Raman Shift / Wavelength' }, labels: { formatter: val => Math.round(val) } },
            stroke: { width: [1.5, 1.5, 2.5] },
            colors: ['#94a3b8', '#ef4444', '#00f0ff']
        };

        if (window.chartInstances["raman"]) {
            window.chartInstances["raman"].updateOptions(options);
        } else {
            window.chartInstances["raman"] = new ApexCharts(document.getElementById("raman-chart"), options);
            window.chartInstances["raman"].render();
        }
    };

    select.addEventListener("change", (e) => updateRamanChart(parseInt(e.target.value)));
    updateRamanChart(0);
};
