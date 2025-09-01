#!/usr/bin/env python3
"""
Generate PDF from README.md file
"""

import subprocess
import sys
import os

def check_and_install_dependencies():
    """Check and install required packages"""
    try:
        import markdown
        import weasyprint
    except ImportError:
        print("Installing required packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown", "weasyprint"])
        print("Packages installed successfully!")
        import markdown
        import weasyprint
    return markdown, weasyprint

def markdown_to_pdf(input_file, output_file):
    """Convert markdown file to PDF"""
    markdown, weasyprint = check_and_install_dependencies()
    
    # Read the markdown file
    with open(input_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert markdown to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['extra', 'codehilite', 'tables', 'toc']
    )
    
    # Add CSS styling for better PDF rendering
    html_with_style = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 100%;
                margin: 0;
                padding: 0;
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                margin-top: 30px;
                margin-bottom: 20px;
                page-break-after: avoid;
            }}
            h2 {{
                color: #34495e;
                border-bottom: 2px solid #ecf0f1;
                padding-bottom: 8px;
                margin-top: 25px;
                margin-bottom: 15px;
                page-break-after: avoid;
            }}
            h3 {{
                color: #34495e;
                margin-top: 20px;
                margin-bottom: 10px;
                page-break-after: avoid;
            }}
            code {{
                background-color: #f4f4f4;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: 'Courier New', Courier, monospace;
                font-size: 0.9em;
            }}
            pre {{
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                overflow-x: auto;
                page-break-inside: avoid;
            }}
            pre code {{
                background-color: transparent;
                padding: 0;
            }}
            blockquote {{
                border-left: 4px solid #3498db;
                margin: 0;
                padding-left: 15px;
                color: #666;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 15px 0;
                page-break-inside: avoid;
            }}
            table th {{
                background-color: #3498db;
                color: white;
                padding: 10px;
                text-align: left;
                border: 1px solid #2980b9;
            }}
            table td {{
                padding: 10px;
                border: 1px solid #ddd;
            }}
            table tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            ul, ol {{
                margin: 10px 0;
                padding-left: 30px;
            }}
            li {{
                margin: 5px 0;
            }}
            a {{
                color: #3498db;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .highlight {{
                background-color: #fff3cd;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Generate PDF
    print(f"Generating PDF from {input_file}...")
    weasyprint.HTML(string=html_with_style).write_pdf(output_file)
    print(f"✅ PDF successfully created: {output_file}")
    
    # Get file size
    file_size = os.path.getsize(output_file)
    file_size_mb = file_size / (1024 * 1024)
    print(f"📄 File size: {file_size_mb:.2f} MB")

if __name__ == "__main__":
    # Generate PDF from README.md
    input_file = "README.md"
    output_file = "README.pdf"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
        sys.exit(1)
    
    try:
        markdown_to_pdf(input_file, output_file)
    except Exception as e:
        print(f"Error generating PDF: {e}")
        print("\nAlternative: You can use online converters like:")
        print("- https://www.markdowntopdf.com/")
        print("- https://md2pdf.netlify.app/")
        sys.exit(1)