from fpdf import FPDF
import re

class PDF(FPDF):
    def header(self):
        # No header for now
        pass

    def footer(self):
        # No footer for now
        pass

def convert_md_to_pdf(md_path, pdf_path):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\n')

        # Handle code blocks (triple backticks)
        if line.startswith('```'):
            # Find the end of the code block
            i += 1
            pdf.set_font("Courier", size=10)
            pdf.set_fill_color(240, 240, 240)
            while i < len(lines) and not lines[i].startswith('```'):
                pdf.cell(0, 6, txt=lines[i].rstrip('\n'), ln=1, fill=True)
                i += 1
            if i < len(lines) and lines[i].startswith('```'):
                i += 1  # skip the closing ```
            pdf.set_font("Arial", size=12)
            continue

        # Handle headings
        if line.startswith('#'):
            level = 0
            for ch in line:
                if ch == '#':
                    level += 1
                else:
                    break
            if level > 0 and level <= 6 and (len(line) > level and line[level] == ' '):
                heading_text = line[level+1:].strip()
                pdf.set_font("Arial", 'B', size=16 - level*2)  # smaller size for higher levels
                pdf.cell(0, 10, txt=heading_text, ln=1)
                pdf.set_font("Arial", size=12)
                i += 1
                continue

        # Handle horizontal rules
        if re.match(r'^\\s*[-*_]{3,}\\s*$', line):
            pdf.ln(5)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
            pdf.ln(5)
            i += 1
            continue

        # Handle blockquotes
        if line.startswith('> '):
            quote_text = line[2:].strip()
            pdf.set_font("Arial", 'I', size=11)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, txt=quote_text, ln=1)
            pdf.set_font("Arial", size=12)
            pdf.set_text_color(0, 0, 0)
            i += 1
            continue

        # Handle lists (unordered)
        if re.match(r'^\\s*[-*]\\s+', line):
            list_text = re.sub(r'^\\s*[-*]\\s+', '', line)
            pdf.cell(10)  # indent
            pdf.cell(0, 6, txt='- ' + list_text, ln=1)
            i += 1
            continue

        # Handle ordered lists
        if re.match(r'^\\s*\\d+\\.\\s+', line):
            list_text = re.sub(r'^\\s*\\d+\\.\\s+', '', line)
            pdf.cell(10)  # indent
            pdf.cell(0, 6, txt=list_text, ln=1)
            i += 1
            continue

        # Handle empty lines
        if line.strip() == '':
            pdf.ln(4)
            i += 1
            continue

        # Handle regular paragraphs (might contain inline markup)
        # We'll just output the line as is for simplicity
        pdf.cell(0, 6, txt=line, ln=1)
        i += 1

    pdf.output(pdf_path)
    print(f"PDF created: {pdf_path}")

if __name__ == "__main__":
    md_file = r"C:\Users\lokes\AI AGENT FIRE WALL\deck pitch\pitch_deck.md"
    pdf_file = r"C:\Users\lokes\AI AGENT FIRE WALL\deck pitch\pitch_deck.pdf"
    convert_md_to_pdf(md_file, pdf_file)