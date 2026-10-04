import markdown
from weasyprint import HTML
import os

# Paths
md_file = r"C:\Users\lokes\AI AGENT FIRE WALL\deck pitch\pitch_deck.md"
pdf_file = r"C:\Users\lokes\AI AGENT FIRE WALL\deck pitch\pitch_deck.pdf"

# Read markdown
with open(md_file, 'r', encoding='utf-8') as f:
    md_content = f.read()

# Convert markdown to HTML
html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])

# Add some basic styling for better PDF appearance
styled_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
        pre {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        code {{ background-color: #f1f2f6; padding: 2px 4px; border-radius: 3px; }}
        blockquote {{ border-left: 4px solid #3498db; margin: 20px 0; padding-left: 20px; color: #555; }}
        ul, ol {{ margin-left: 20px; }}
        .page-break {{ page-break-after: always; }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>
"""

# Convert HTML to PDF
HTML(string=styled_html).write_pdf(pdf_file)

print(f"PDF successfully created: {pdf_file}")