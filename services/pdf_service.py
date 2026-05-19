import io
import os
from datetime import datetime
from flask import current_app
from fpdf import FPDF

class PDFService:
    @staticmethod
    def generate_budget_report(budget, expenses, category_names):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        font_dir = os.path.join(project_root, 'static', 'fonts')

        total_actual = sum(e.actual_amount for e in expenses)
        remaining = budget.amount - total_actual
        
        cat_summary = {}
        for e in expenses:
            name = category_names.get(e.category_id, "Unknown")
            if name not in cat_summary:
                cat_summary[name] = {'count': 0, 'total': 0.0}
            cat_summary[name]['count'] += 1
            cat_summary[name]['total'] += e.actual_amount

        class ReportPDF(FPDF):
            def footer(self):
                self.set_y(-15)
                self.set_font('ArmenianFont', '', 8)
                self.set_text_color(128)
                self.cell(0, 10, f'Page {self.page_no()} | Budget: {budget.id}', 0, 0, 'C')

        pdf = ReportPDF()
        reg_font = os.path.join(font_dir, 'NotoSansArmenian-Regular.ttf')
        bold_font = os.path.join(font_dir, 'NotoSansArmenian-Bold.ttf')
        pdf.add_font('ArmenianFont', '', reg_font, uni=True)
        pdf.add_font('ArmenianFont', 'B', bold_font, uni=True)
       
        pdf.add_page()
        pdf.set_font("ArmenianFont", 'B', 20)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 15, txt="Բյուջեի զեկուցում", ln=True)
        
        pdf.set_font("ArmenianFont", size=10)
        pdf.set_text_color(100)
        pdf.cell(0, 5, txt=f"Բյուջե: {budget.id} | Generated: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)

    
        pdf.set_fill_color(235, 245, 255)
        pdf.rect(10, pdf.get_y(), 190, 35, 'F')
        pdf.set_xy(15, pdf.get_y() + 5)
        
        pdf.set_font("ArmenianFont", 'B', 11)
        pdf.cell(60, 10, f"Լիմիտ: {budget.amount:,.2f}")
        pdf.cell(60, 10, f"Իրական ծախսել: {total_actual:,.2f}")
        pdf.cell(60, 10, f"Մնացած: {remaining:,.2f}", ln=True)

        pdf.ln(15)

        
        pdf.set_font("ArmenianFont", 'B', 12)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 10, "Կատեգորիայի օգտագործում", ln=True)
        
        pdf.set_font("ArmenianFont", 'B', 10)
        pdf.set_fill_color(200, 220, 240)
        pdf.cell(80, 10, " Կատեգորիա", border=1, fill=True)
        pdf.cell(40, 10, " Օգտա-ած անգամ", border=1, fill=True, align='C')
        pdf.cell(70, 10, " Ընդհատված գումար", border=1, fill=True, ln=True, align='C')

        pdf.set_font("ArmenianFont", size=10)
        pdf.set_text_color(0)
        for name, data in cat_summary.items():
            pdf.cell(80, 10, f" {name}", border=1)
            pdf.cell(40, 10, f"{data['count']}", border=1, align='C')
            pdf.cell(70, 10, f"{data['total']:,.2f} {budget.currency}", border=1, ln=True, align='R')

        pdf.ln(10)

        
        pdf.set_font("ArmenianFont", 'B', 12)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 10, "Մանրամասն ծախսեր (պլանավորված և իրական)", ln=True)

    
        w_desc = 55
        w_cat = 40
        w_plan = 32
        w_actu = 32
        w_diff = 31

        pdf.set_font("ArmenianFont", 'B', 9)
        pdf.set_fill_color(44, 62, 80)
        pdf.set_text_color(255)
        pdf.cell(w_desc, 10, " Նկարագրություն", border=1, fill=True)
        pdf.cell(w_cat, 10, " Կատեգորիա", border=1, fill=True)
        pdf.cell(w_plan, 10, " Պլանավորված", border=1, fill=True, align='C')
        pdf.cell(w_actu, 10, " Իրական", border=1, fill=True, align='C')
        pdf.cell(w_diff, 10, " Տարբերություն", border=1, fill=True, ln=True, align='C')

        pdf.set_font("ArmenianFont", size=9)
        pdf.set_text_color(0)
        for e in expenses:
            
            cat_name = category_names.get(e.category_id, "N/A")
            diff = e.amount - e.actual_amount
            pdf.cell(w_desc, 10, f" {e.description[:35]}", border=1)
            pdf.cell(w_cat, 10, f" {cat_name}", border=1)
            pdf.cell(w_plan, 10, f"{e.amount:,.2f}", border=1, align='R')
            pdf.cell(w_actu, 10, f"{e.actual_amount:,.2f}", border=1, align='R')
            
            
            if diff < 0: pdf.set_text_color(200, 0, 0) 
            else: pdf.set_text_color(0, 120, 0)
            
            pdf.cell(w_diff, 10, f"{diff:,.2f}", border=1, ln=True, align='R')
            pdf.set_text_color(0)


        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)
        return pdf_output