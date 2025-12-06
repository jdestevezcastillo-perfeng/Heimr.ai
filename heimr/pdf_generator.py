# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
PDF Report Generator for Heimr
Converts Markdown reports to professional PDF documents
"""
import markdown
from weasyprint import HTML, CSS
from datetime import datetime


class PDFGenerator:
    """Generate PDF reports from Markdown content."""

    # CSS styling for professional PDF reports
    PDF_CSS = """
    @page {
        size: A4;
        margin: 2cm;
        @top-center {
            content: "Heimr Performance Analysis Report";
            font-family: 'DejaVu Sans', sans-serif;
            font-size: 10pt;
            color: #666;
        }
        @bottom-right {
            content: "Page " counter(page) " of " counter(pages);
            font-family: 'DejaVu Sans', sans-serif;
            font-size: 9pt;
            color: #666;
        }
    }

    body {
        font-family: 'DejaVu Sans', 'Arial', sans-serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #333;
    }

    h1 {
        color: #2c3e50;
        font-size: 24pt;
        border-bottom: 3px solid #3498db;
        padding-bottom: 10px;
        margin-top: 20px;
        page-break-before: always;
    }

    h1:first-of-type {
        page-break-before: avoid;
    }

    h2 {
        color: #34495e;
        font-size: 18pt;
        border-bottom: 2px solid #95a5a6;
        padding-bottom: 8px;
        margin-top: 16px;
    }

    h3 {
        color: #7f8c8d;
        font-size: 14pt;
        margin-top: 12px;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
        font-size: 10pt;
    }

    th {
        background-color: #3498db;
        color: white;
        padding: 10px;
        text-align: left;
        font-weight: bold;
    }

    td {
        padding: 8px;
        border-bottom: 1px solid #ddd;
    }

    tr:nth-child(even) {
        background-color: #f8f9fa;
    }

    tr:hover {
        background-color: #e8f4f8;
    }

    code {
        background-color: #f4f4f4;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'DejaVu Sans Mono', 'Courier New', monospace;
        font-size: 9pt;
    }

    pre {
        background-color: #f8f9fa;
        border-left: 4px solid #3498db;
        padding: 15px;
        overflow-x: auto;
        border-radius: 4px;
    }

    pre code {
        background-color: transparent;
        padding: 0;
    }

    blockquote {
        border-left: 4px solid #95a5a6;
        padding-left: 15px;
        margin-left: 0;
        color: #7f8c8d;
        font-style: italic;
    }

    ul, ol {
        margin: 10px 0;
        padding-left: 30px;
    }

    li {
        margin: 5px 0;
    }

    strong {
        color: #2c3e50;
        font-weight: bold;
    }

    em {
        font-style: italic;
        color: #555;
    }

    .status-pass {
        color: #27ae60;
        font-weight: bold;
    }

    .status-fail {
        color: #e74c3c;
        font-weight: bold;
    }

    .status-warn {
        color: #f39c12;
        font-weight: bold;
    }

    /* Page breaks */
    .page-break {
        page-break-after: always;
    }

    /* Avoid breaking inside elements */
    table, pre, blockquote {
        page-break-inside: avoid;
    }

    h1, h2, h3 {
        page-break-after: avoid;
    }
    """

    def __init__(self):
        """Initialize PDF generator."""
        self.md = markdown.Markdown(extensions=[
            'tables',
            'fenced_code',
            'codehilite',
            'nl2br',
            'sane_lists'
        ])

    def generate_pdf(self, markdown_content: str, output_path: str):
        """
        Convert markdown content to PDF.

        Args:
            markdown_content: Markdown text to convert
            output_path: Path to save the PDF file
        """
        # Convert markdown to HTML
        html_content = self.md.convert(markdown_content)

        # Wrap in HTML document structure
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Heimr Performance Analysis Report</title>
        </head>
        <body>
            <div class="report-header">
                <h1 style="border-bottom: none; text-align: center; color: #3498db;">
                    ⚡ Heimr Performance Analysis
                </h1>
                <p style="text-align: center; color: #7f8c8d; font-size: 10pt;">
                    Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
                <hr style="border: none; border-top: 2px solid #3498db; margin: 20px 0;">
            </div>
            {html_content}
        </body>
        </html>
        """

        # Generate PDF
        HTML(string=full_html).write_pdf(
            output_path,
            stylesheets=[CSS(string=self.PDF_CSS)]
        )

    def generate_from_file(self, markdown_file: str, output_path: str):
        """
        Convert markdown file to PDF.

        Args:
            markdown_file: Path to markdown file
            output_path: Path to save the PDF file
        """
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        self.generate_pdf(markdown_content, output_path)
