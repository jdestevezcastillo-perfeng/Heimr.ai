// ===== Heimr Documentation Page =====

const GITHUB_RAW_BASE = 'https://raw.githubusercontent.com/jdestevezcastillo-perfeng/Heimr.ai/main/docs/wiki/';

const DOC_TITLES = {
    '01-quickstart': 'Quick Start',
    '02-architecture': 'Architecture',
    '03-cli-reference': 'CLI Reference',
    '04-configuration': 'Configuration',
    '05-ai-analysis-engine': 'AI Analysis Engine',
    '06-python-api': 'Python API',
    '07-reporting': 'Reporting',
    '08-ci-cd-integration': 'CI/CD Integration',
    '09-failure-scenarios': 'Failure Scenarios',
    '10-troubleshooting': 'Troubleshooting',
    '11-development': 'Development Guide'
};

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Mermaid with dark theme
    mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        themeVariables: {
            primaryColor: '#00ffa3',
            primaryTextColor: '#ccd6f6',
            primaryBorderColor: '#64ffda',
            lineColor: '#64ffda',
            secondaryColor: '#0a192f',
            tertiaryColor: '#112240'
        }
    });
    initDocs();
    initMobileNav();
});

async function initDocs() {
    const urlParams = new URLSearchParams(window.location.search);
    const docName = urlParams.get('doc');

    const loadingEl = document.getElementById('doc-loading');
    const errorEl = document.getElementById('doc-error');
    const contentEl = document.getElementById('doc-content');

    // Highlight active sidebar link
    updateActiveSidebarLink(docName);

    if (!docName) {
        // No doc specified, show welcome page
        loadingEl.style.display = 'none';
        errorEl.style.display = 'block';
        return;
    }

    try {
        const markdown = await fetchDoc(docName);

        // Configure marked
        marked.setOptions({
            breaks: true,
            gfm: true
        });

        // Render markdown
        contentEl.innerHTML = marked.parse(markdown);

        // Update page title
        if (DOC_TITLES[docName]) {
            document.title = `${DOC_TITLES[docName]} - Heimr.ai Docs`;
        }

        // Process internal links
        processInternalLinks(contentEl);

        // Render Mermaid diagrams
        await renderMermaidDiagrams(contentEl);

        // Hide loading, show content
        loadingEl.style.display = 'none';
        contentEl.style.display = 'block';

    } catch (error) {
        console.error('Error loading doc:', error);
        loadingEl.style.display = 'none';
        errorEl.innerHTML = `
            <h2>❌ Error Loading Documentation</h2>
            <p>Could not load "${docName}.md". The document may not exist or there may be a network issue.</p>
            <div class="quick-links">
                <a href="?doc=01-quickstart" class="btn btn--primary">🚀 Quick Start</a>
                <a href="index.html" class="btn btn--secondary">← Back to Home</a>
            </div>
        `;
        errorEl.style.display = 'block';
    }
}

async function fetchDoc(docName) {
    const url = `${GITHUB_RAW_BASE}${docName}.md`;

    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }

    let markdown = await response.text();

    // Remove the "← Back to Index" link that's in the source files
    markdown = markdown.replace(/\[← Back to Index\]\(.*?\)\n*/g, '');

    return markdown;
}

function updateActiveSidebarLink(docName) {
    document.querySelectorAll('.sidebar-link').forEach(link => {
        const linkDoc = link.getAttribute('data-doc');
        if (linkDoc === docName) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

async function renderMermaidDiagrams(container) {
    // Find all code blocks that contain mermaid diagrams
    const codeBlocks = container.querySelectorAll('pre code');

    for (let i = 0; i < codeBlocks.length; i++) {
        const code = codeBlocks[i];
        const text = code.textContent.trim();

        // Check if this is a mermaid diagram (starts with flowchart, graph, sequenceDiagram, etc.)
        if (text.match(/^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|gitgraph)/)) {
            try {
                const { svg } = await mermaid.render(`mermaid-${i}`, text);
                const wrapper = document.createElement('div');
                wrapper.className = 'mermaid-diagram';
                wrapper.innerHTML = svg;
                code.parentElement.replaceWith(wrapper);
            } catch (error) {
                console.warn('Mermaid render error:', error);
                // Keep the original code block if rendering fails
            }
        }
    }
}

function processInternalLinks(container) {
    // Convert relative markdown links to docs.html links
    container.querySelectorAll('a').forEach(link => {
        const href = link.getAttribute('href');

        if (!href) return;

        // Convert wiki links like "02-architecture.md" to "?doc=02-architecture"
        if (href.match(/^\d{2}-[\w-]+\.md$/)) {
            const docName = href.replace('.md', '');
            link.setAttribute('href', `?doc=${docName}`);
        }

        // Add target="_blank" for external links
        if (href.startsWith('http') && !href.includes('heimr.ai')) {
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');
        }
    });
}

function initMobileNav() {
    const toggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (!toggle || !navLinks) return;

    toggle.addEventListener('click', () => {
        navLinks.classList.toggle('active');
        toggle.classList.toggle('active');
    });

    navLinks.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            navLinks.classList.remove('active');
            toggle.classList.remove('active');
        });
    });
}
