from markdown_pdf import MarkdownPdf, Section
import sys

try:
    pdf = MarkdownPdf(toc_level=2)
    md_file = "submission/CSE440_Final_Report.md"
    with open(md_file, "r", encoding="utf-8") as f:
        text = f.read()
    
    pdf.add_section(Section(text))
    pdf.save("submission/CSE440_Final_Report.pdf")
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
