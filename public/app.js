// Configure Axios global defaults to include HttpOnly session cookies
axios.defaults.withCredentials = true;

// State management
let uploadedFiles = [];
let currentOriginalPlots = {};
let currentDiagnoses = {};
let currentPipelineData = null;

document.addEventListener("DOMContentLoaded", () => {
    lucide.createIcons();
    checkBackendStatus();
    setupUploadZone();
    setupFormHandlers();
    setupVisualizationSwitchers();
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
    const fileCountEl = document.getElementById("selected-files-count");
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

    if (uploadedFiles.length === 0) {
        fileCountEl.textContent = "No files selected";
    } else {
        const totalBytes = uploadedFiles.reduce((acc, file) => acc + file.size, 0);
        let sizeText = "";
        if (totalBytes < 1024) {
            sizeText = `${totalBytes} B`;
        } else if (totalBytes < 1024 * 1024) {
            sizeText = `${(totalBytes / 1024).toFixed(2)} KB`;
        } else {
            sizeText = `${(totalBytes / (1024 * 1024)).toFixed(2)} MB`;
        }
        fileCountEl.textContent = `Total Files Selected: ${uploadedFiles.length} (${sizeText})`;
    }

    submitBtn.disabled = uploadedFiles.length === 0;
    lucide.createIcons();
}

window.removeFile = function(index) {
    uploadedFiles.splice(index, 1);
    updateFileBadges();
};

function setupFormHandlers() {
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

function setupVisualizationSwitchers() {
    const btnInteractive = document.getElementById("btn-show-interactive");
    const btnOriginal = document.getElementById("btn-show-original");
    const btnReset = document.getElementById("btn-reset-dashboard");
    const btnDownloadAll = document.getElementById("btn-download-all-plots");
    const chartsGrid = document.getElementById("charts-grid");
    const originalGrid = document.getElementById("original-plots-grid");

    btnInteractive.addEventListener("click", () => {
        btnInteractive.classList.add("active");
        btnOriginal.classList.remove("active");
        chartsGrid.style.display = "grid";
        originalGrid.style.display = "none";
        btnDownloadAll.style.display = "none";
    });

    btnOriginal.addEventListener("click", () => {
        btnOriginal.classList.add("active");
        btnInteractive.classList.remove("active");
        chartsGrid.style.display = "none";
        originalGrid.style.display = "grid";
        btnDownloadAll.style.display = "inline-flex";
        renderOriginalPlotsList();
    });

    // Download All Plots Event (Triggers clean selection between Images ZIP and Report PDF)
    btnDownloadAll.addEventListener("click", (e) => {
        e.stopPropagation();
        const keys = Object.keys(currentOriginalPlots);
        if (keys.length === 0) {
            showToast("No original plots available for download.");
            return;
        }

        // Toggle existing selection dropdown if already visible
        const existingDropdown = document.getElementById("export-plots-dropdown");
        if (existingDropdown) {
            existingDropdown.classList.add("fade-out");
            setTimeout(() => existingDropdown.remove(), 200);
            return;
        }

        // Create styled floating context selection menu
        const dropdown = document.createElement("div");
        dropdown.id = "export-plots-dropdown";
        dropdown.className = "export-plots-dropdown glass-card fade-in";
        
        dropdown.innerHTML = `
            <button class="export-dropdown-item" id="export-zip-btn">
                <i data-lucide="archive"></i> Download Images (ZIP)
            </button>
            <button class="export-dropdown-item" id="export-pdf-btn">
                <i data-lucide="file-text"></i> Download Report (PDF)
            </button>
        `;

        // Position dropdown perfectly underneath the trigger button
        const rect = btnDownloadAll.getBoundingClientRect();
        dropdown.style.position = "absolute";
        dropdown.style.top = `${window.scrollY + rect.bottom + 8}px`;
        dropdown.style.left = `${window.scrollX + rect.left}px`;
        dropdown.style.minWidth = `${rect.width}px`;
        dropdown.style.zIndex = "1000";

        document.body.appendChild(dropdown);
        lucide.createIcons();

        // Safe self-closing handle when user clicks away
        const closeDropdown = (event) => {
            const el = document.getElementById("export-plots-dropdown");
            if (el && !el.contains(event.target) && event.target !== btnDownloadAll) {
                el.classList.add("fade-out");
                setTimeout(() => el.remove(), 200);
                document.removeEventListener("click", closeDropdown);
            }
        };
        setTimeout(() => {
            document.addEventListener("click", closeDropdown);
        }, 0);

        // ZIP Exporter Callback
        document.getElementById("export-zip-btn").addEventListener("click", () => {
            showToast("Packaging all original plots into ZIP archive...");
            
            let plotsToExport = {};
            if (currentPipelineData && currentPipelineData.plots && currentPipelineData.plots.multi_stage) {
                const stageLabels = {
                    raw: "Raw",
                    snv: "SNV",
                    sg: "Savgol",
                    mc: "MeanCentered"
                };
                currentPipelineData.plots.active_stages.forEach(stageKey => {
                    const stageObj = currentPipelineData.plots.stages[stageKey];
                    if (stageObj && stageObj.original_plots) {
                        const labelPrefix = stageLabels[stageKey] || stageKey.toUpperCase();
                        Object.entries(stageObj.original_plots).forEach(([key, base64Str]) => {
                            const capitalizedKey = key.charAt(0).toUpperCase() + key.slice(1);
                            plotsToExport[`${labelPrefix} ${capitalizedKey}`] = base64Str;
                        });
                    }
                });
            } else {
                plotsToExport = currentOriginalPlots;
            }

            axios.post("/ai/export-zip", {
                plots: plotsToExport
            }, {
                responseType: "blob"
            })
            .then(res => {
                const blob = new Blob([res.data], { type: "application/zip" });
                const link = document.createElement("a");
                link.href = window.URL.createObjectURL(blob);
                link.download = "spectroscopy_plots.zip";
                link.click();
                showToast("ZIP download started successfully!");
            })
            .catch(err => {
                showToast("Failed to compile ZIP: " + err.message);
            });
        });

        // PDF Exporter Callback
        document.getElementById("export-pdf-btn").addEventListener("click", () => {
            showToast("Generating comprehensive scientific diagnostics report (PDF)...");
            
            let plotsToExport = {};
            if (currentPipelineData && currentPipelineData.plots && currentPipelineData.plots.multi_stage) {
                const stageLabels = {
                    raw: "Raw",
                    snv: "SNV",
                    sg: "Savgol",
                    mc: "MeanCentered"
                };
                currentPipelineData.plots.active_stages.forEach(stageKey => {
                    const stageObj = currentPipelineData.plots.stages[stageKey];
                    if (stageObj && stageObj.original_plots) {
                        const labelPrefix = stageLabels[stageKey] || stageKey.toUpperCase();
                        Object.entries(stageObj.original_plots).forEach(([key, base64Str]) => {
                            const capitalizedKey = key.charAt(0).toUpperCase() + key.slice(1);
                            plotsToExport[`${labelPrefix} ${capitalizedKey}`] = base64Str;
                        });
                    }
                });
            } else {
                plotsToExport = currentOriginalPlots;
            }

            axios.post("/ai/export-pdf", {
                plots: plotsToExport,
                diagnoses: currentDiagnoses
            }, {
                responseType: "blob"
            })
            .then(res => {
                const blob = new Blob([res.data], { type: "application/pdf" });
                const link = document.createElement("a");
                link.href = window.URL.createObjectURL(blob);
                link.download = "spectroscopy_scientific_report.pdf";
                link.click();
                showToast("PDF report downloaded successfully!");
            })
            .catch(err => {
                showToast("Failed to compile scientific report PDF. Make sure reportlab and pillow are installed.");
            });
        });
    });

    btnReset.addEventListener("click", () => {
        uploadedFiles = [];
        currentPipelineData = null;
        const uploader = document.getElementById("upload-zone");
        const existingList = uploader.querySelector(".file-list-preview");
        if (existingList) existingList.remove();
        
        const countBadge = document.getElementById("selected-files-count");
        if (countBadge) {
            countBadge.textContent = "0 files selected";
            countBadge.style.display = "none";
        }
        
        document.getElementById("pipeline-form").reset();
        document.getElementById("study-context").value = "";
        document.getElementById("sg-options").style.display = "none";
        
        Object.values(window.chartInstances).forEach(chart => chart.destroy());
        window.chartInstances = {};
        currentOriginalPlots = {};
        currentDiagnoses = {};
        
        document.getElementById("dashboard-content").style.display = "none";
        document.getElementById("empty-state").style.display = "flex";
        document.getElementById("stages-tracker-container").style.display = "none";
        btnDownloadAll.style.display = "none";
        
        showToast("Dashboard reset successfully. Ready for a new run!");
    });
}

function executePipeline() {
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

    if (algorithm === "PLS") {
        const classes = new Set(uploadedFiles.map(f => f.name[0].toUpperCase()));
        if (classes.size < 2) {
            alert("PLS requires files from at least 2 distinct classes (based on the first letter of filenames, e.g. A1... and B1...).");
            return;
        }
    }

    const submitBtn = document.getElementById("submit-btn");
    submitBtn.innerHTML = `<i data-lucide="loader" class="animate-spin"></i> Processing...`;
    submitBtn.disabled = true;

    // Show Progress Bar and animate steps
    const progressContainer = document.getElementById("progress-container");
    const progressBarFill = document.getElementById("progress-bar-fill");
    const progressText = document.getElementById("progress-text");

    progressContainer.style.display = "flex";
    progressBarFill.style.width = "5%";
    progressText.textContent = "Sanitizing input parameters...";

    let progress = 5;
    const progressInterval = setInterval(() => {
        if (progress < 90) {
            progress += Math.floor(Math.random() * 10) + 3;
            if (progress > 90) progress = 90;
            progressBarFill.style.width = `${progress}%`;
            
            if (progress < 30) {
                progressText.textContent = "Parsing spectroscopy binary headers...";
            } else if (progress < 60) {
                progressText.textContent = "Aligning wavelength resolutions and coordinate matrices...";
            } else {
                progressText.textContent = "Applying Standard Normal Variate (SNV) and Savitzky-Golay equations...";
            }
        }
    }, 150);

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
            clearInterval(progressInterval);
            progressBarFill.style.width = "100%";
            progressText.textContent = "Projections complete! Rendering views...";
            setTimeout(() => {
                progressContainer.style.display = "none";
                renderDashboard(response.data);
            }, 500);
        })
        .catch(error => {
            clearInterval(progressInterval);
            progressContainer.style.display = "none";
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
    currentPipelineData = data;
    document.getElementById("empty-state").style.display = "none";
    const dashboard = document.getElementById("dashboard-content");
    dashboard.style.display = "block";

    // Keep switcher default on Interactive
    document.getElementById("btn-show-interactive").classList.add("active");
    document.getElementById("btn-show-original").classList.remove("active");
    document.getElementById("charts-grid").style.display = "grid";
    document.getElementById("original-plots-grid").style.display = "none";

    // Set stats
    document.getElementById("stat-algo").textContent = data.algorithm;
    document.getElementById("stat-format").textContent = data.detected_format.toUpperCase();
    document.getElementById("stat-count").textContent = data.samples_count;
    document.getElementById("stat-wl").textContent = `${data.wavelengths_count} pts`;

    const stagesTracker = document.getElementById("stages-tracker-container");
    const pillsContainer = document.getElementById("stages-pills");

    if (data.plots.multi_stage) {
        stagesTracker.style.display = "flex";
        pillsContainer.innerHTML = "";
        
        const labels = {
            raw: "Raw Spectra",
            snv: "SNV Spectra",
            sg: "Savitzky-Golay",
            mc: "Mean Centered"
        };

        data.plots.active_stages.forEach(stageKey => {
            const pill = document.createElement("button");
            pill.type = "button";
            pill.className = "stage-pill";
            pill.textContent = labels[stageKey] || stageKey.toUpperCase();
            pill.addEventListener("click", () => {
                document.querySelectorAll(".stage-pill").forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                selectStageData(data.plots.stages[stageKey], data.algorithm);
            });
            pillsContainer.appendChild(pill);
        });

        // Click the final preprocessed stage by default
        document.querySelectorAll(".stage-pill")[data.plots.active_stages.length - 1].click();
    } else {
        stagesTracker.style.display = "none";
        selectStageData(data.plots, data.algorithm);
    }
}

function selectStageData(stageObj, algorithm) {
    const grid = document.getElementById("charts-grid");
    grid.innerHTML = "";
    Object.values(window.chartInstances).forEach(chart => chart.destroy());
    window.chartInstances = {};

    currentOriginalPlots = stageObj.original_plots || {};

    if (algorithm === "PCA") {
        window.createChartCard(grid, "scree-chart", "Scree Plot (Explained Variance)");
        window.createChartCard(grid, "scores-chart", "PCA Scores Plot (PC1 vs PC2)");
        window.createChartCard(grid, "loadings-chart", "PCA Loadings Plot");
        window.createChartCard(grid, "residuals-chart", "Hotelling's T² vs Q Residuals");

        window.renderScreePlot(stageObj.plots.scree);
        window.renderScoresPlot(stageObj.plots.scores, "pc1", "pc2", "PC1", "PC2");
        window.renderLoadingsPlot(stageObj.plots.loadings, ["pc1", "pc2"], ["PC1 Loading", "PC2 Loading"]);
        window.renderResidualsPlot(stageObj.plots.residuals);
    } else if (algorithm === "PLS") {
        window.createChartCard(grid, "scores-chart", "PLS-DA Scores Plot (Comp 1 vs Comp 2)");
        window.createChartCard(grid, "loadings-chart", "PLS Loadings Plot");

        window.renderScoresPlot(stageObj.plots.scores, "comp1", "comp2", "PLS Comp 1", "PLS Comp 2");
        window.renderLoadingsPlot(stageObj.plots.loadings, ["comp1", "comp2"], ["Comp 1 Loading", "Comp 2 Loading"]);
    } else if (algorithm === "RAMAN") {
        window.createRamanCard(grid);
        window.renderRamanSpectra(stageObj.plots);
    }

    if (document.getElementById("btn-show-original").classList.contains("active")) {
        renderOriginalPlotsList();
    }
}

function renderOriginalPlotsList() {
    const grid = document.getElementById("original-plots-grid");
    grid.innerHTML = "";
    
    const titles = {
        spectra: "Original Spectral Lines Plot",
        scores: "Original Scores Projection Plot",
        scree: "Original Scree Variance Plot",
        loadings: "Original Loadings Line Profiles",
        heatmap: "Original PCA1 scores Heatmap Grid",
        raman: "Original Raman Baseline Overlay"
    };

    Object.entries(currentOriginalPlots).forEach(([key, base64Str]) => {
        const titleText = titles[key] || key.toUpperCase() + " Plot";
        const card = document.createElement("div");
        card.className = "original-plot-card glass-card";
        
        card.innerHTML = `
            <div class="original-plot-card-header">
                <h3>${titleText}</h3>
            </div>
            <img src="data:image/png;base64,${base64Str}" alt="${key} plot">
            <div class="original-plot-actions">
                <button class="original-plot-btn btn-download-single">
                    <i data-lucide="download"></i> Download PNG
                </button>
                <button class="original-plot-btn primary btn-ai-analyze">
                    <i data-lucide="brain"></i> AI Diagnose Plot
                </button>
            </div>
            <div class="ai-diagnosis-wrapper" style="display: none;"></div>
        `;
        
        // Single image downloader
        card.querySelector(".btn-download-single").addEventListener("click", () => {
            downloadSinglePlot(base64Str, `${key}_plot.png`);
        });

        // Vision AI analyzer agent
        card.querySelector(".btn-ai-analyze").addEventListener("click", (e) => {
            executeVisionAiAnalysis(base64Str, titleText, card.querySelector(".ai-diagnosis-wrapper"), e.currentTarget);
        });

        grid.appendChild(card);
    });
    
    // Refresh lucide icons inside the newly generated grid
    lucide.createIcons();
}

function downloadSinglePlot(base64Str, filename) {
    const link = document.createElement("a");
    link.href = `data:image/png;base64,${base64Str}`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast(`Downloading ${filename}...`);
}

function executeVisionAiAnalysis(base64Str, plotType, container, button) {
    const context = document.getElementById("study-context").value.trim();
    
    button.disabled = true;
    button.innerHTML = `<i data-lucide="loader" class="animate-spin"></i> Analyzing...`;
    lucide.createIcons();

    container.style.display = "block";
    container.innerHTML = `
        <div class="ai-diagnosis-container glass-card">
            <div class="ai-diagnosis-title">
                <i data-lucide="bot"></i> AI Scientific Diagnostics
            </div>
            <div class="ai-diagnosis-content">
                <span class="pulse-dot" style="display: inline-block; margin-right: 8px;"></span> Consultant reviewing visual features and data projections...
            </div>
        </div>
    `;
    lucide.createIcons();

    axios.post("/ai/analyze-plot", {
        image_base64: base64Str,
        plot_type: plotType,
        context: context
    })
    .then(response => {
        button.disabled = false;
        button.innerHTML = `<i data-lucide="brain"></i> Re-Diagnose`;
        lucide.createIcons();

        if (response.data.success) {
            const rawAnalysis = response.data.analysis;
            currentDiagnoses[plotType] = rawAnalysis;
            
            // Render beautiful diagnostic panel with header actions & interactive Q&A
            container.innerHTML = `
                <div class="ai-diagnosis-container glass-card">
                    <div class="ai-diagnosis-header">
                        <div class="ai-diagnosis-title">
                            <i data-lucide="bot"></i> AI Scientific Diagnostics
                        </div>
                        <button class="original-plot-btn copy-btn" style="padding: 4px 10px; font-size: 11px;">
                            <i data-lucide="copy" style="width: 12px; height: 12px;"></i> Copy
                        </button>
                    </div>
                    <div class="ai-diagnosis-content">${formatMarkdownResponse(rawAnalysis)}</div>
                    
                    <!-- Q&A Interactive Thread -->
                    <div class="ai-qa-section">
                        <div class="ai-qa-header">
                            <i data-lucide="message-square"></i> Ask a question about this plot
                        </div>
                        <div class="ai-qa-response-box" style="display: none;"></div>
                        <div class="ai-qa-input-wrapper">
                            <input type="text" class="ai-qa-input" placeholder="Ask a question about this specific ${plotType}...">
                            <button class="original-plot-btn primary ask-btn" style="padding: 8px 14px;">
                                <i data-lucide="send" style="width: 12px; height: 12px;"></i> Ask
                            </button>
                        </div>
                    </div>
                </div>
            `;
            lucide.createIcons();

            // Bind Copy Button Handler
            const copyBtn = container.querySelector(".copy-btn");
            copyBtn.addEventListener("click", () => {
                let copyPromise;
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    copyPromise = navigator.clipboard.writeText(rawAnalysis);
                } else {
                    const textarea = document.createElement("textarea");
                    textarea.value = rawAnalysis;
                    textarea.style.position = "fixed";
                    textarea.style.opacity = "0";
                    document.body.appendChild(textarea);
                    textarea.select();
                    try {
                        document.execCommand("copy");
                        copyPromise = Promise.resolve();
                    } catch (e) {
                        copyPromise = Promise.reject(e);
                    }
                    document.body.removeChild(textarea);
                }

                copyPromise
                    .then(() => {
                        copyBtn.innerHTML = `<i data-lucide="check" style="color: var(--success); width: 12px; height: 12px;"></i> Copied!`;
                        lucide.createIcons();
                        showToast("Diagnostics copied to clipboard!");
                        setTimeout(() => {
                            copyBtn.innerHTML = `<i data-lucide="copy" style="width: 12px; height: 12px;"></i> Copy`;
                            lucide.createIcons();
                        }, 2000);
                    })
                    .catch(err => {
                        showToast("Failed to copy text: " + err);
                    });
            });

            // Bind Q&A Submit Handlers
            const qaInput = container.querySelector(".ai-qa-input");
            const askBtn = container.querySelector(".ask-btn");
            const responseBox = container.querySelector(".ai-qa-response-box");

            const submitQuestion = () => {
                const questionText = qaInput.value.trim();
                if (!questionText) return;

                // Disable input during request
                qaInput.disabled = true;
                askBtn.disabled = true;
                askBtn.innerHTML = `<i data-lucide="loader" class="animate-spin" style="width: 12px; height: 12px;"></i> Asking...`;
                lucide.createIcons();

                // Append interactive block containing user query and active loader placeholder
                const chatBlock = document.createElement("div");
                chatBlock.className = "chat-history-block";
                chatBlock.innerHTML = `
                    <div class="chat-user-msg">
                        <span class="chat-sender">You:</span> ${questionText}
                    </div>
                    <div class="chat-ai-msg loading-msg">
                        <span class="chat-sender"><i data-lucide="sparkles" style="width: 12px; height: 12px; color: var(--primary);"></i> AI Response:</span>
                        <span class="pulse-loading" style="color: var(--text-secondary);">
                            <span class="pulse-dot"></span> Consulting RAG and formulating analysis...
                        </span>
                    </div>
                `;
                responseBox.appendChild(chatBlock);
                responseBox.style.display = "block";
                lucide.createIcons();

                // Clear input box immediately so researcher can type their next query
                qaInput.value = "";

                axios.post("/ai/ask-question", {
                    plot_type: plotType,
                    question: questionText
                })
                .then(qaRes => {
                    qaInput.disabled = false;
                    askBtn.disabled = false;
                    askBtn.innerHTML = `<i data-lucide="send" style="width: 12px; height: 12px;"></i> Ask`;
                    lucide.createIcons();

                    const aiMsgElement = chatBlock.querySelector(".chat-ai-msg");
                    aiMsgElement.classList.remove("loading-msg");

                    if (qaRes.data.success) {
                        aiMsgElement.innerHTML = `
                            <span class="chat-sender"><i data-lucide="sparkles" style="width: 12px; height: 12px; color: var(--primary);"></i> AI Response:</span>
                            <div class="ai-qa-answer-text">${formatMarkdownResponse(qaRes.data.answer)}</div>
                        `;
                        lucide.createIcons();
                    } else {
                        aiMsgElement.innerHTML = `
                            <span class="chat-sender" style="color: var(--danger);"><i data-lucide="alert-triangle" style="width: 12px; height: 12px;"></i> AI Error:</span>
                            <div class="ai-qa-answer-text" style="color: var(--danger);">${qaRes.data.error || "Failed to formulate response."}</div>
                        `;
                        lucide.createIcons();
                    }
                })
                .catch(err => {
                    qaInput.disabled = false;
                    askBtn.disabled = false;
                    askBtn.innerHTML = `<i data-lucide="send" style="width: 12px; height: 12px;"></i> Ask`;
                    lucide.createIcons();

                    const aiMsgElement = chatBlock.querySelector(".chat-ai-msg");
                    aiMsgElement.classList.remove("loading-msg");
                    aiMsgElement.innerHTML = `
                        <span class="chat-sender" style="color: var(--danger);"><i data-lucide="alert-triangle" style="width: 12px; height: 12px;"></i> Connection Error:</span>
                        <div class="ai-qa-answer-text" style="color: var(--danger);">${err.message}</div>
                    `;
                    lucide.createIcons();
                });
            };

            askBtn.addEventListener("click", submitQuestion);
            qaInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter") {
                    submitQuestion();
                }
            });

        } else {
            container.innerHTML = `
                <div class="ai-diagnosis-container glass-card" style="border-left-color: #ff3b30;">
                    <div class="ai-diagnosis-title" style="color: #ff3b30;">
                        <i data-lucide="alert-triangle"></i> Diagnostics Failed
                    </div>
                    <div class="ai-diagnosis-content">${response.data.error || "Unknown VLM error. Please try again."}</div>
                </div>
            `;
            lucide.createIcons();
        }
    })
    .catch(error => {
        button.disabled = false;
        button.innerHTML = `<i data-lucide="brain"></i> AI Diagnose Plot`;
        lucide.createIcons();

        container.innerHTML = `
            <div class="ai-diagnosis-container glass-card" style="border-left-color: #ff3b30;">
                <div class="ai-diagnosis-title" style="color: #ff3b30;">
                    <i data-lucide="alert-triangle"></i> Connection Error
                </div>
                <div class="ai-diagnosis-content">Failed to reach the AI endpoint: ${error.message}</div>
            </div>
        `;
        lucide.createIcons();
    });
}

function formatMarkdownResponse(text) {
    if (!text) return "";
    
    // Clean up excessive decorative separator characters (like ====, ----, _____, »»»»)
    let cleanedText = text.replace(/[=\-_»~—_]{3,}/g, "");

    // Elegant regex mapping for headers and lists to make the output extremely high-fidelity
    let html = cleanedText
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/### (.*?)\n/g, '<h3>$1</h3>')
        .replace(/## (.*?)\n/g, '<h3>$1</h3>')
        .replace(/# (.*?)\n/g, '<h3>$1</h3>')
        .replace(/^\s*\*\s+(.*?)$/gm, '<li>$1</li>')
        .replace(/^\s*-\s+(.*?)$/gm, '<li>$1</li>');
        
    // Wrap consecutive list items in ul blocks
    html = html.replace(/(<li>.*?<\/li>)+/g, match => `<ul>${match}</ul>`);
    return html;
}

function showToast(message) {
    const existing = document.querySelector(".toast-notice");
    if (existing) existing.remove();
    
    const toast = document.createElement("div");
    toast.className = "toast-notice";
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.remove(), 2500);
}

