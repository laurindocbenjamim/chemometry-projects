// State management
let uploadedFiles = [];
let chartInstances = {};

document.addEventListener("DOMContentLoaded", () => {
    lucide.createIcons();
    checkBackendStatus();
    setupUploadZone();
    setupFormHandlers();
});

function checkBackendStatus() {
    axios.get("/docs")
        .then(() => {
            const statusIndicator = document.getElementById("api-status");
            statusIndicator.textContent = "Backend Connected";
            statusIndicator.style.color = "#10b981";
        })
        .catch(() => {
            const statusIndicator = document.getElementById("api-status");
            statusIndicator.textContent = "API Offline";
            statusIndicator.style.color = "#ef4444";
        });
}

function setupUploadZone() {
    const zone = document.getElementById("upload-zone");
    const input = document.getElementById("file-input");
    const browseBtn = document.getElementById("browse-btn");

    browseBtn.addEventListener("click", () => input.click());
    input.addEventListener("change", (e) => handleFiles(e.target.files));

    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("dragover");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
    zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("dragover");
        handleFiles(e.dataTransfer.files);
    });
}

function handleFiles(files) {
    const formatSelect = document.getElementById("file-format").value;
    const errors = [];

    for (let file of files) {
        const ext = file.name.split(".").pop().toLowerCase();
        
        // 1. Frontend validation: size and extension checks
        if (ext !== "csv" && ext !== "sp") {
            errors.push(`'${file.name}' has invalid type. Supported formats: .csv, .sp`);
            continue;
        }
        if (file.size > 5 * 1024 * 1024) {
            errors.push(`'${file.name}' exceeds the 5MB size limit.`);
            continue;
        }
        if (formatSelect !== "auto" && ext !== formatSelect) {
            errors.push(`'${file.name}' doesn't match chosen expected format: ${formatSelect.toUpperCase()}`);
            continue;
        }

        // Avoid duplicates
        if (!uploadedFiles.some(f => f.name === file.name)) {
            uploadedFiles.push(file);
        }
    }

    if (errors.length > 0) alert(errors.join("\n"));
    updateFileBadges();
}

function updateFileBadges() {
    const container = document.getElementById("file-list");
    const submitBtn = document.getElementById("submit-btn");
    container.innerHTML = "";

    uploadedFiles.forEach((file, index) => {
        const badge = document.createElement("div");
        badge.className = "file-badge";
        badge.innerHTML = `
            <i data-lucide="file-text" style="width: 12px; height: 12px; color: var(--primary);"></i>
            <span>${file.name}</span>
            <button type="button" onclick="removeFile(${index})">&times;</button>
        `;
        container.appendChild(badge);
    });

    submitBtn.disabled = uploadedFiles.length === 0;
    lucide.createIcons();
}

window.removeFile = function(index) {
    uploadedFiles.splice(index, 1);
    updateFileBadges();
};

function setupFormHandlers() {
    const sgFilter = document.getElementById("snv"); // Toggle SG visual Panel
    const sgCheck = document.getElementById("sg-filter");
    const sgOptions = document.getElementById("sg-options");
    const form = document.getElementById("pipeline-form");

    sgCheck.addEventListener("change", (e) => {
        sgOptions.style.display = e.target.checked ? "block" : "none";
    });

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        executePipeline();
    });
}

function executePipeline() {
    // 2. Validate SG filter options
    const algorithm = document.getElementById("algorithm").value;
    const sgChecked = document.getElementById("sg-filter").checked;
    const windowLen = parseInt(document.getElementById("sg-window").value);
    const polyOrder = parseInt(document.getElementById("sg-poly").value);

    if (sgChecked) {
        if (windowLen % 2 === 0) {
            alert("Savitzky-Golay window length must be odd!");
            return;
        }
        if (polyOrder >= windowLen) {
            alert("SG Polynomial Order must be strictly less than the window length!");
            return;
        }
    }

    // Validate PLS multiple classes requirement
    if (algorithm === "PLS") {
        const classes = new Set(uploadedFiles.map(f => f.name[0].toUpperCase()));
        if (classes.size < 2) {
            alert("PLS is a supervised algorithm and requires files belonging to at least 2 distinct classes (based on the first character of filenames, e.g., 'A1...' and 'B1...').");
            return;
        }
    }

    const submitBtn = document.getElementById("submit-btn");
    submitBtn.innerHTML = `<i data-lucide="loader" class="animate-spin"></i> Processing...`;
    submitBtn.disabled = true;

    // Create request configuration matching Pydantic PipelineRequest
    const config = {
        algorithm: algorithm,
        format: document.getElementById("file-format").value,
        preprocessing: {
            snv: document.getElementById("snv").checked,
            sg_filter: sgChecked,
            sg_window_length: windowLen,
            sg_polyorder: polyOrder,
            sg_deriv: parseInt(document.getElementById("sg-deriv").value),
            mean_center: document.getElementById("mean-center").checked
        }
    };

    const formData = new FormData();
    uploadedFiles.forEach(file => formData.append("files", file));
    formData.append("config", JSON.stringify(config));

    axios.post("/api/v1/pca/process", formData)
        .then(response => {
            renderDashboard(response.data);
        })
        .catch(error => {
            const msg = error.response?.data?.detail || "Pipeline processing failed.";
            alert(msg);
        })
        .finally(() => {
            submitBtn.innerHTML = `<i data-lucide="play"></i> Execute Analysis`;
            submitBtn.disabled = false;
            lucide.createIcons();
        });
}

function renderDashboard(data) {
    document.getElementById("empty-state").style.display = "none";
    const dashboard = document.getElementById("dashboard-content");
    dashboard.style.display = "block";

    // Set stats
    document.getElementById("stat-algo").textContent = data.algorithm;
    document.getElementById("stat-format").textContent = data.detected_format.toUpperCase();
    document.getElementById("stat-count").textContent = data.samples_count;
    document.getElementById("stat-wl").textContent = `${data.wavelengths_count} pts`;

    // Clear previous charts
    const grid = document.getElementById("charts-grid");
    grid.innerHTML = "";
    Object.values(chartInstances).forEach(chart => chart.destroy());
    chartInstances = {};

    const algo = data.algorithm;
    if (algo === "PCA") {
        createChartCard(grid, "scree-chart", "Scree Plot (Explained Variance)");
        createChartCard(grid, "scores-chart", "PCA Scores Plot (PC1 vs PC2)");
        createChartCard(grid, "loadings-chart", "PCA Loadings Plot");
        createChartCard(grid, "residuals-chart", "Hotelling's T² vs Q Residuals");

        renderScreePlot(data.plots.scree);
        renderScoresPlot(data.plots.scores, "pc1", "pc2", "PC1", "PC2");
        renderLoadingsPlot(data.plots.loadings, ["pc1", "pc2"], ["PC1 Loading", "PC2 Loading"]);
        renderResidualsPlot(data.plots.residuals);
    } else if (algo === "PLS") {
        createChartCard(grid, "scores-chart", "PLS-DA Scores Plot (Comp 1 vs Comp 2)");
        createChartCard(grid, "loadings-chart", "PLS Loadings Plot");

        renderScoresPlot(data.plots.scores, "comp1", "comp2", "PLS Comp 1", "PLS Comp 2");
        renderLoadingsPlot(data.plots.loadings, ["comp1", "comp2"], ["Comp 1 Loading", "Comp 2 Loading"]);
    } else if (algo === "RAMAN") {
        // Raman card gets a select element to toggle sample view
        createRamanCard(grid);
        renderRamanSpectra(data.plots);
    }
}

function createChartCard(parent, id, title) {
    const card = document.createElement("div");
    card.className = "chart-card glass-card";
    card.innerHTML = `<h3>${title}</h3><div id="${id}"></div>`;
    parent.appendChild(card);
}

function createRamanCard(parent) {
    const card = document.createElement("div");
    card.className = "chart-card glass-card";
    card.style.gridColumn = "1 / -1"; // Stretch across entire layout
    card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <h3>RAMAN Spectroscopy - ALS Baseline Correction</h3>
            <select id="raman-sample-select" style="padding: 6px 12px; font-size: 13px;"></select>
        </div>
        <div id="raman-chart"></div>
    `;
    parent.appendChild(card);
}

// Chart renderers utilizing ApexCharts
function renderScreePlot(scree) {
    const options = {
        chart: { type: 'bar', height: 320, toolbar: { show: false }, background: 'transparent' },
        theme: { mode: 'dark' },
        series: [{ name: 'Variance Ratio', data: scree.variance.map(v => parseFloat((v * 100).toFixed(2))) }],
        xaxis: { categories: scree.labels },
        colors: ['#00f0ff'],
        yaxis: { title: { text: 'Percentage (%)' } }
    };
    chartInstances["scree"] = new ApexCharts(document.getElementById("scree-chart"), options);
    chartInstances["scree"].render();
}

function renderScoresPlot(scores, xKey, yKey, xLabel, yLabel) {
    // Group series by class
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
    chartInstances["scores"] = new ApexCharts(document.getElementById("scores-chart"), options);
    chartInstances["scores"].render();
}

function renderLoadingsPlot(loadings, keys, names) {
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
    chartInstances["loadings"] = new ApexCharts(document.getElementById("loadings-chart"), options);
    chartInstances["loadings"].render();
}

function renderResidualsPlot(residuals) {
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
    chartInstances["residuals"] = new ApexCharts(document.getElementById("residuals-chart"), options);
    chartInstances["residuals"].render();
}

function renderRamanSpectra(plots) {
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

        if (chartInstances["raman"]) {
            chartInstances["raman"].updateOptions(options);
        } else {
            chartInstances["raman"] = new ApexCharts(document.getElementById("raman-chart"), options);
            chartInstances["raman"].render();
        }
    };

    select.addEventListener("change", (e) => updateRamanChart(parseInt(e.target.value)));
    updateRamanChart(0);
}
