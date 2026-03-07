# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
HTML Report Generator for Heimr.
Generates standalone HTML reports with interactive Plotly charts.
"""
import markdown
from datetime import datetime


class HTMLReportGenerator:
    """Generate standalone HTML reports from Markdown content."""
    
    HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Heimr Performance Analysis Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

    <style>
        :root {{
            /* Colors from Heimr.ai website */
            --bg-primary: #0a192f;
            --bg-secondary: #0d1b2a;
            --bg-card: rgba(13, 27, 42, 0.7);
            
            /* Gradient colors (cyan to teal from logo) */
            --accent-cyan: #00d9ff;
            --accent-teal: #00ffa3;
            --accent-glow-cyan: rgba(0, 217, 255, 0.3);
            --accent-glow-teal: rgba(0, 255, 163, 0.3);
            
            /* Text colors */
            --text-primary: #e6f1ff;
            --text-secondary: #8892b0;
            --text-muted: #5a6a8a;
            
            /* Status colors */
            --success: #22C55E;
            --warning: #F59E0B;
            --danger: #EF4444;
            
            /* Fonts */
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: var(--font-sans);
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        /* Animated background matching website */
        .bg-gradient {{
            position: fixed;
            inset: 0;
            background:
                radial-gradient(ellipse 80% 50% at 50% -20%, var(--accent-glow-cyan), transparent),
                radial-gradient(ellipse 60% 40% at 80% 100%, var(--accent-glow-teal), transparent),
                linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
            z-index: -2;
        }}
        
        .circuit-lines {{
            position: fixed;
            inset: 0;
            z-index: -1;
            opacity: 0.03;
            background-image:
                linear-gradient(var(--accent-cyan) 1px, transparent 1px),
                linear-gradient(90deg, var(--accent-cyan) 1px, transparent 1px);
            background-size: 50px 50px;
            mask-image: radial-gradient(ellipse at center, black 20%, transparent 70%);
        }}
        
        /* Header with Heimr branding */
        .report-header {{
            background: rgba(10, 25, 47, 0.9);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(0, 255, 163, 0.15);
            padding: 1.5rem 2rem;
            display: flex;
            flex-direction: row;
            align-items: center;
            justify-content: center;
            gap: 1.5rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .header-logo {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .logo-img {{
            height: 85px;
            filter: drop-shadow(0 0 8px var(--accent-glow-teal));
        }}
        
        .logo-text {{
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-teal));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .header-subtitle {{
            font-size: 1.8rem;
            font-weight: 600;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-teal));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
            position: relative;
        }}
        
        h1 {{
            font-size: 2rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-teal));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        h2 {{
            font-size: 1.5rem;
            margin-top: 2rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--bg-secondary);
            color: var(--text-primary);
        }}
        
        h3 {{
            font-size: 1.2rem;
            color: var(--text-secondary);
            margin-top: 1.5rem;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            background: var(--bg-card);
            border: 1px solid rgba(0, 255, 163, 0.1);
            border-radius: 12px;
            overflow: hidden;
            backdrop-filter: blur(10px);
        }}
        
        th {{
            background: linear-gradient(135deg, rgba(0, 217, 255, 0.2), rgba(0, 255, 163, 0.2));
            color: var(--text-primary);
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            border-bottom: 1px solid rgba(0, 255, 163, 0.2);
        }}
        
        td {{
            padding: 12px 16px;
            border-bottom: 1px solid rgba(0, 255, 163, 0.05);
        }}
        
        tr:hover {{
            background: rgba(0, 255, 163, 0.05);
        }}
        
        code {{
            background: rgba(0, 255, 163, 0.1);
            border: 1px solid rgba(0, 255, 163, 0.2);
            padding: 2px 8px;
            border-radius: 6px;
            font-family: var(--font-mono);
            font-size: 0.9em;
            color: var(--accent-teal);
        }}
        
        blockquote {{
            border-left: 4px solid var(--accent-teal);
            margin: 1rem 0;
            padding: 1rem 1.5rem;
            background: rgba(0, 255, 163, 0.08);
            border-radius: 0 12px 12px 0;
        }}
        
        hr {{
            border: none;
            border-top: 1px solid rgba(0, 255, 163, 0.15);
            margin: 2rem 0;
        }}
        
        ul, ol {{
            padding-left: 1.5rem;
            margin: 1rem 0;
        }}
        
        li {{
            margin: 0.5rem 0;
        }}
        
        strong {{
            color: var(--text-primary);
        }}
        
        /* Status banners */
        .status-ok {{ 
            border-left: 4px solid var(--success); 
            background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(34, 197, 94, 0.05));
            padding: 1.5rem;
            border-radius: 0 12px 12px 0;
        }}
        
        .status-warning {{ 
            border-left: 4px solid var(--warning); 
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05));
            padding: 1.5rem;
            border-radius: 0 12px 12px 0;
        }}
        
        .status-failed {{ 
            border-left: 4px solid var(--danger); 
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.05));
            padding: 1.5rem;
            border-radius: 0 12px 12px 0;
        }}
        
        /* Print styles */
        @media print {{
            .bg-gradient, .circuit-lines, .report-header {{
                display: none;
            }}
            
            body {{
                background: white;
                color: #333;
            }}
            
            .container {{
                max-width: 100%;
                padding: 20px;
            }}
            
            h1, h2 {{
                color: #333;
                background: none;
                -webkit-text-fill-color: #333;
            }}
            
            table {{
                background: #f8f9fa;
                border: 1px solid #ddd;
            }}
            
            th {{
                background: #e9ecef;
                color: #333;
            }}
            
            code {{
                background: #f1f3f5;
                color: #333;
            }}
            
            blockquote {{
                background: #f8f9fa;
            }}
            
            .js-plotly-plot {{
                page-break-inside: avoid;
            }}
        }}
        
        .footer {{
            margin-top: 3rem;
            padding: 2rem;
            border-top: 1px solid rgba(0, 255, 163, 0.1);
            text-align: center;
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        
        .footer a {{
            color: var(--accent-teal);
            text-decoration: none;
        }}
        
        .footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="bg-gradient"></div>
    <div class="circuit-lines"></div>
    
    <header class="report-header">
        <div class="header-logo">
            <img class="logo-img" src="data:image/png;base64,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" alt="Heimr">
        </div>
        <span class="header-subtitle">Performance Analysis Report</span>
    </header>
    
    <div class="container">
        {content}
        <div class="footer">
            Generated by <a href="https://heimr.ai"><strong>Heimr.ai</strong></a> on {timestamp}<br>
            <em>Print this page (Ctrl+P) to save as PDF</em>
        </div>
    </div>
</body>
</html>'''

    def __init__(self):
        """Initialize HTML generator."""
        self.md = markdown.Markdown(extensions=[
            'tables',
            'fenced_code',
            'codehilite',
            'nl2br',
            'sane_lists',
            'md_in_html'  # Allow HTML passthrough
        ])
    
    def generate_html(self, markdown_content: str, output_path: str):
        """
        Convert markdown content to standalone HTML.
        
        Args:
            markdown_content: Markdown text with embedded Plotly HTML
            output_path: Path to save the HTML file
        """
        # Convert markdown to HTML (Plotly HTML passes through)
        html_content = self.md.convert(markdown_content)
        
        # Wrap in template
        full_html = self.HTML_TEMPLATE.format(
            content=html_content,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
    
    def generate_from_file(self, markdown_file: str, output_path: str):
        """
        Convert markdown file to HTML.
        
        Args:
            markdown_file: Path to markdown file
            output_path: Path to save the HTML file
        """
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        self.generate_html(markdown_content, output_path)
