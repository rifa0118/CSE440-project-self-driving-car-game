from markdown_pdf import MarkdownPdf, Section
import sys

try:
    pdf = MarkdownPdf(toc_level=2)
    md_file = "/Users/isti115/.gemini/antigravity-ide/brain/435af699-85c8-4914-a07a-3fe9478a7043/system_architecture.md"
    with open(md_file, "r", encoding="utf-8") as f:
        text = f.read()
    
    pdf.add_section(Section(text))
    pdf.save("submission/System_Architecture.pdf")
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
