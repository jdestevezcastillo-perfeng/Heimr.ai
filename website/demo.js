document.addEventListener('DOMContentLoaded', () => {
    // Modal Logic
    const modal = document.getElementById("demo-modal");
    const btn = document.getElementById("open-demo-btn");
    const span = document.getElementsByClassName("close-modal")[0];

    btn.onclick = () => modal.style.display = "block";
    span.onclick = () => modal.style.display = "none";
    window.onclick = (event) => {
        if (event.target == modal) modal.style.display = "none";
    }

    // Drag and Drop Logic
    const dropArea = document.getElementById('drop-area');
    const fileElem = document.getElementById('fileElem');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.remove('dragover'), false);
    });

    dropArea.addEventListener('drop', handleDrop, false);
    dropArea.addEventListener('click', () => fileElem.click());
    fileElem.addEventListener('change', handleFiles, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles({ target: { files: files } });
    }

    async function handleFiles(e) {
        const files = e.target.files;
        if (files.length > 0) {
            uploadFiles(files);
        }
    }

    async function uploadFiles(files) {
        const formData = new FormData();
        // Append all files with the same key "files" (FastAPI expects List[UploadFile])
        for (let i = 0; i < files.length; i++) {
            formData.append("files", files[i]);
        }

        // UI Updates
        document.getElementById('drop-area').style.display = 'none';
        const statusArea = document.getElementById('status-area');
        const statusText = document.getElementById('status-text');
        const loader = document.querySelector('.loader');

        statusArea.style.display = 'block';
        loader.style.display = 'block';
        statusText.innerText = `Uploading ${files.length} file(s)...`;

        try {
            // NOTE: In production, point to the actual backend URL
            const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

            const response = await fetch(`${API_BASE}/api/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error("Upload failed");

            const data = await response.json();
            const jobId = data.job_id;

            statusText.innerText = "Analyzing... (This uses a local LLM, please wait ~30s)";
            pollStatus(jobId, API_BASE);

        } catch (error) {
            console.error(error);
            statusText.innerText = "Error: " + error.message;
            loader.style.display = 'none';
        }
    }

    async function pollStatus(jobId, apiBase) {
        const statusText = document.getElementById('status-text');
        const loader = document.querySelector('.loader');
        const reportContent = document.getElementById('report-content');

        const interval = setInterval(async () => {
            try {
                const res = await fetch(`${apiBase}/api/status/${jobId}`);
                const data = await res.json();

                if (data.status === 'COMPLETED') {
                    clearInterval(interval);
                    statusText.innerText = "Analysis Complete!";
                    loader.style.display = 'none';

                    // Fetch Report
                    const reportRes = await fetch(`${apiBase}${data.report_url}`);
                    const markdownText = await reportRes.text();

                    // Render Markdown
                    reportContent.innerHTML = marked.parse(markdownText);

                    // Add Download Buttons
                    const controls = document.createElement('div');
                    controls.style.marginTop = '10px';
                    controls.innerHTML = `
                        <button id="btn-dl-md" class="btn btn--secondary" style="padding: 5px 10px; font-size: 0.8rem; margin-right: 10px;">Download MD</button>
                        <button id="btn-dl-pdf" class="btn btn--secondary" style="padding: 5px 10px; font-size: 0.8rem;">Download PDF</button>
                    `;
                    // Insert controls before report content
                    reportContent.parentNode.insertBefore(controls, reportContent);

                    // Handlers
                    document.getElementById('btn-dl-md').onclick = () => {
                        const blob = new Blob([markdownText], { type: 'text/markdown' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `heimr-report-${data.job_id}.md`;
                        a.click();
                        URL.revokeObjectURL(url);
                    };

                    document.getElementById('btn-dl-pdf').onclick = () => {
                        // Download from server
                        const url = `${apiBase}/api/report/${data.job_id}/pdf`;
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `heimr-report-${data.job_id}.pdf`; // Filename typically handled by Content-Disposition but good fallback
                        a.click();
                    };

                } else if (data.status === 'PROCESSING') {
                    if (data.partial_report) {
                        statusText.innerText = "Generating Insight...";
                        // Stream the LLM output live
                        // We prepend a header since partial report is just the raw text
                        const partialHtml = marked.parse(data.partial_report);
                        reportContent.innerHTML = `<h3>Live Analysis...</h3><div class="streaming-text">${partialHtml}</div>`;
                    }
                } else if (data.status === 'FAILED') {
                    clearInterval(interval);
                    statusText.innerText = "Analysis Failed: " + data.message;
                    loader.style.display = 'none';
                }
            } catch (e) {
                console.error(e);
            }
        }, 2000);
    }
});
