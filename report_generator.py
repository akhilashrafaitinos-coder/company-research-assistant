"""
report_generator.py
--------------------
Turns the structured company dict into a professional PDF.
Uses fpdf2. Includes every field the spec requires:
  Company Name, Website, Phone, Address, Products/Services,
  AI-generated Pain Points, Competitor Name + Website.
"""

from fpdf import FPDF, XPos, YPos
from datetime import datetime


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 30, 30)
        self.cell(0, 10, "Company Research Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(20, 20, 20)
        self.ln(3)
        self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(200, 200, 200)
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(3)

    def body_text(self, text):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def bullet_list(self, items):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(50, 50, 50)
        for item in items:
            self.multi_cell(0, 6, f"-  {item}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def key_value(self, label, value):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(20, 20, 20)
        self.cell(35, 6, f"{label}:")
        self.set_font("Helvetica", "", 11)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, value or "N/A", new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _safe(text):
    """fpdf2's default fonts don't support all unicode - strip anything risky."""
    if not isinstance(text, str):
        text = str(text)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_pdf_report(data: dict, output_path: str = "company_report.pdf") -> str:
    pdf = ReportPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, _safe(data.get("company_name", "Unknown Company")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.section_title("Company Information")
    pdf.key_value("Website", _safe(data.get("website", "N/A")))
    pdf.key_value("Phone", _safe(data.get("phone", "N/A")))
    pdf.key_value("Address", _safe(data.get("address", "N/A")))

    pdf.section_title("Overview")
    pdf.body_text(_safe(data.get("description", "N/A")))

    pdf.section_title("Products & Services")
    pdf.bullet_list([_safe(x) for x in data.get("products_services", [])] or ["N/A"])

    pdf.section_title("AI-Generated Pain Points")
    pdf.bullet_list([_safe(x) for x in data.get("pain_points", [])] or ["N/A"])

    pdf.section_title("Competitors")
    competitors = data.get("competitors", [])
    if competitors:
        for c in competitors:
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 6, _safe(c.get("name", "Unknown")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 6, _safe(c.get("website", "Website not found")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)
    else:
        pdf.body_text("N/A")

    pdf.output(output_path)
    return output_path
