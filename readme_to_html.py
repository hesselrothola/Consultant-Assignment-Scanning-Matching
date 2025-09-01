#!/usr/bin/env python3
"""
Convert README.md to a formatted HTML file that can be printed to PDF
"""

import re
import html

def markdown_to_html(md_text):
    """Simple markdown to HTML converter"""
    
    # Escape HTML
    lines = md_text.split('\n')
    html_lines = []
    in_code_block = False
    in_table = False
    
    for line in lines:
        # Handle code blocks
        if line.startswith('```'):
            if in_code_block:
                html_lines.append('</pre>')
                in_code_block = False
            else:
                html_lines.append('<pre>')
                in_code_block = True
            continue
        
        if in_code_block:
            html_lines.append(html.escape(line))
            continue
        
        # Handle tables
        if '|' in line and not line.strip().startswith('#'):
            if not in_table:
                html_lines.append('<table>')
                in_table = True
            
            # Check if it's a separator line
            if all(c in '-|: ' for c in line):
                continue
            
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            if any(cells):
                row_type = 'th' if html_lines[-1] == '<table>' else 'td'
                row = '<tr>' + ''.join(f'<{row_type}>{html.escape(cell)}</{row_type}>' for cell in cells) + '</tr>'
                html_lines.append(row)
            continue
        elif in_table:
            html_lines.append('</table>')
            in_table = False
        
        # Handle headers
        if line.startswith('#'):
            level = len(line.split()[0])
            text = line[level:].strip()
            html_lines.append(f'<h{level}>{html.escape(text)}</h{level}>')
            continue
        
        # Handle lists
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            text = line.strip()[2:]
            # Handle inline code
            text = re.sub(r'`([^`]+)`', r'<code>\1</code>', html.escape(text))
            # Handle bold
            text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
            html_lines.append(f'<li>{text}</li>')
            continue
        
        # Handle blockquotes
        if line.startswith('>'):
            text = line[1:].strip()
            html_lines.append(f'<blockquote>{html.escape(text)}</blockquote>')
            continue
        
        # Handle empty lines
        if not line.strip():
            html_lines.append('<br>')
            continue
        
        # Regular paragraphs
        text = html.escape(line)
        # Handle inline code
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        # Handle bold
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        # Handle links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        html_lines.append(f'<p>{text}</p>')
    
    if in_table:
        html_lines.append('</table>')
    if in_code_block:
        html_lines.append('</pre>')
    
    return '\n'.join(html_lines)

def create_html_document(content):
    """Create a complete HTML document with styling"""
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Consultant Assignment Matching System - README</title>
    <style>
        @media print {
            body {{ margin: 0; }
            .no-print {{ display: none; }
        }}
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fff;
        }
        
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 30px;
            margin-bottom: 20px;
        }
        
        h2 {
            color: #34495e;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
            margin-top: 25px;
            margin-bottom: 15px;
        }
        
        h3 {
            color: #34495e;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        h4 {
            color: #555;
            margin-top: 15px;
            margin-bottom: 8px;
        }
        
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9em;
            color: #d14;
        }
        
        pre {
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            overflow-x: auto;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9em;
            line-height: 1.4;
        }
        
        blockquote {
            border-left: 4px solid #3498db;
            margin: 15px 0;
            padding-left: 15px;
            color: #666;
            font-style: italic;
        }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }
        
        table th {
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            border: 1px solid #2980b9;
            font-weight: bold;
        }
        
        table td {
            padding: 10px 12px;
            border: 1px solid #ddd;
        }
        
        table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        table tr:hover {
            background-color: #f5f5f5;
        }
        
        ul, ol {
            margin: 15px 0;
            padding-left: 30px;
        }
        
        li {
            margin: 8px 0;
        }
        
        a {
            color: #3498db;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
            color: #2980b9;
        }
        
        strong {
            color: #2c3e50;
            font-weight: 600;
        }
        
        .header-info {
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .no-print {
            margin: 20px 0;
            padding: 15px;
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 5px;
        }
        
        @media screen {
            body {
                background-color: #f5f5f5;
            }
            
            body > * {
                background-color: white;
                padding: 40px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border-radius: 8px;
            }
        }
    </style>
</head>
<body>
    <div class="no-print">
        <strong>📄 PDF Generation:</strong> Use your browser's Print function (Cmd+P or Ctrl+P) and select "Save as PDF" to create a PDF version of this document.
    </div>
    
    <div class="header-info">
        <h1 style="border: none; margin: 0;">Consultant Assignment Matching System</h1>
        <p style="margin: 10px 0 0 0;">AI-driven agent for the Swedish consulting market</p>
    </div>
    
    {content}
</body>
</html>"""
    
    return html_template.replace('{content}', content)

# Read README.md
with open('README.md', 'r', encoding='utf-8') as f:
    readme_content = f.read()

# Convert to HTML
html_content = markdown_to_html(readme_content)
full_html = create_html_document(html_content)

# Write HTML file
output_file = 'README.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(full_html)

print(f"✅ HTML file created: {output_file}")
print("\n📄 To create a PDF:")
print("1. Open README.html in your browser")
print("2. Press Cmd+P (Mac) or Ctrl+P (Windows/Linux)")
print("3. Select 'Save as PDF' as the destination")
print("4. Click 'Save'\n")
print("The HTML file has been styled for optimal PDF generation.")