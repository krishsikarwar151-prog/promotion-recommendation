"""
PDF/CSV report generation for the Employee Promotion Prediction System.
Uses ReportLab for PDF output.
"""
import io
import datetime
import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
def generate_employee_pdf(employee_data: dict, prediction: int, probability: float,
                           explanation: dict, gaps: list, development_plan: dict) -> bytes:
    """
    Generate a professional PDF assessment report for a single employee.

    Returns bytes suitable for st.download_button.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2.5*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        PRIMARY_COLOR  = colors.HexColor('#2563EB')
        SUCCESS_COLOR  = colors.HexColor('#16A34A')
        DANGER_COLOR   = colors.HexColor('#DC2626')
        HEADER_BG      = colors.HexColor('#F0F4FF')

        title_style = ParagraphStyle('Title', parent=styles['Title'],
                                     fontSize=18, textColor=PRIMARY_COLOR,
                                     fontName='Helvetica-Bold', spaceAfter=4)
        h1_style = ParagraphStyle('H1', parent=styles['Heading1'],
                                  fontSize=13, textColor=PRIMARY_COLOR,
                                  fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=4)
        body_style = ParagraphStyle('Body', parent=styles['Normal'],
                                    fontSize=10, leading=14, spaceAfter=6)
        small_style = ParagraphStyle('Small', parent=styles['Normal'],
                                     fontSize=8.5, leading=12, textColor=colors.grey)
        disclaimer_style = ParagraphStyle('Disc', parent=styles['Normal'],
                                          fontSize=8, leading=11, textColor=colors.HexColor('#7C3AED'),
                                          borderPad=4, borderColor=colors.HexColor('#7C3AED'),
                                          borderWidth=0.5, backColor=colors.HexColor('#F5F3FF'))

        story = []

        # ── Header ────────────────────────────────────────────────────────────
        story.append(Paragraph("PromotionAI — Employee Assessment Report", title_style))
        story.append(Paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", small_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_COLOR, spaceAfter=10))

        # ── Employee Details ──────────────────────────────────────────────────
        story.append(Paragraph("1. Employee Information", h1_style))
        emp_data_rows = [
            ['Employee Name', employee_data.get('name', 'N/A'),
             'Employee ID', str(employee_data.get('employee_id', 'N/A'))],
            ['Department', employee_data.get('department', 'N/A'),
             'Region', str(employee_data.get('region', 'N/A'))],
            ['Education', employee_data.get('education', 'N/A'),
             'Gender', employee_data.get('gender', 'N/A')],
            ['Age', f"{employee_data.get('age', 'N/A')} yrs",
             'Length of Service', f"{employee_data.get('length_of_service', 'N/A')} yrs"],
            ['Recruitment Channel', employee_data.get('recruitment_channel', 'N/A'),
             'No. of Trainings', str(employee_data.get('no_of_trainings', 'N/A'))],
            ['Avg Training Score', f"{employee_data.get('avg_training_score', 'N/A')}/100",
             'Prev Year Rating', f"{employee_data.get('previous_year_rating', 'N/A')}/5"],
            ['KPIs Met >80%', 'Yes' if employee_data.get('KPIs_met >80%', 0) else 'No',
             'Award Won', 'Yes' if employee_data.get('awards_won?', 0) else 'No'],
        ]
        emp_table = Table(emp_data_rows, colWidths=[4*cm, 5.5*cm, 3.5*cm, 4.5*cm])
        emp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), HEADER_BG),
            ('BACKGROUND', (2, 0), (2, -1), HEADER_BG),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), ['#FFFFFF', '#F8FAFC']),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(emp_table)
        story.append(Spacer(1, 12))

        # ── Model Prediction ──────────────────────────────────────────────────
        story.append(Paragraph("2. Model Prediction", h1_style))
        pred_label = "PROMOTED" if prediction == 1 else "NOT PROMOTED"
        pred_color = SUCCESS_COLOR if prediction == 1 else DANGER_COLOR
        pred_style = ParagraphStyle('Pred', parent=styles['Normal'],
                                    fontSize=13, fontName='Helvetica-Bold', textColor=pred_color)
        story.append(Paragraph(f"Outcome: {pred_label}   |   Probability: {probability*100:.1f}%", pred_style))
        story.append(Paragraph(
            "NOTE: This is a model estimate based on historical patterns and does not constitute "
            "an official promotion decision. Human review is required.", small_style
        ))
        story.append(Spacer(1, 10))

        # ── Key Drivers ───────────────────────────────────────────────────────
        story.append(Paragraph("3. Key Factors Influencing This Prediction", h1_style))
        story.append(Paragraph("Factors supporting promotion:", body_style))
        for item in explanation.get('top_positive', [])[:5]:
            clean = item.replace('**', '').replace('`', '')
            story.append(Paragraph(f"  ✓  {clean}", body_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Factors associated with lower score:", body_style))
        for item in explanation.get('top_negative', [])[:5]:
            clean = item.replace('**', '').replace('`', '')
            story.append(Paragraph(f"  ✗  {clean}", body_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph(explanation.get('disclaimer', ''), disclaimer_style))
        story.append(Spacer(1, 10))

        # ── Skill Gaps ────────────────────────────────────────────────────────
        if gaps:
            story.append(Paragraph("4. Skill Gap Analysis", h1_style))
            for gap in gaps:
                clean_desc = gap['gap_description'].replace('**', '').replace('`', '')
                story.append(Paragraph(
                    f"[{gap['priority']}]  {gap['name']}: {clean_desc}", body_style
                ))
            story.append(Spacer(1, 6))

        # ── Development Plan ─────────────────────────────────────────────────
        story.append(Paragraph("5. 90-Day Development Plan", h1_style))
        clean_summary = development_plan.get('summary', '').replace('**', '')
        story.append(Paragraph(clean_summary, body_style))
        if development_plan.get('timeline'):
            plan_rows = [['Timeframe', 'Focus Area', 'Recommended Action', 'Priority']]
            for item in development_plan['timeline']:
                plan_rows.append([
                    item.get('window', ''),
                    item.get('area', ''),
                    item.get('action', ''),
                    item.get('priority', '')
                ])
            plan_table = Table(plan_rows, colWidths=[3.5*cm, 4.5*cm, 7*cm, 2.5*cm])
            plan_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8.5),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), ['#FFFFFF', '#F8FAFC']),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(plan_table)

        story.append(Spacer(1, 12))

        # ── Footer ────────────────────────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#E2E8F0')))
        story.append(Paragraph(
            "PromotionAI | This report is generated by an AI model and is intended as a decision-support tool only. "
            "All final promotion decisions must be made by qualified HR personnel following organizational policy.",
            small_style
        ))

        doc.build(story)
        pdf_bytes = buf.getvalue()
        buf.close()
        return pdf_bytes

    except ImportError:
        # ReportLab not available — return a plain-text fallback
        lines = [
            "PROMOTIONAI — EMPLOYEE ASSESSMENT REPORT",
            f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 60,
            "",
            "1. EMPLOYEE INFORMATION",
        ]
        for k, v in employee_data.items():
            lines.append(f"  {k}: {v}")
        lines += [
            "",
            "2. MODEL PREDICTION",
            f"  Outcome: {'PROMOTED' if prediction else 'NOT PROMOTED'}",
            f"  Probability: {probability*100:.1f}%",
            "",
            "  NOTE: Model estimate only. Human HR review required.",
        ]
        return "\n".join(lines).encode('utf-8')


def generate_bulk_csv(result_df: pd.DataFrame) -> bytes:
    """Return a CSV bytes object for bulk prediction results download."""
    return result_df.to_csv(index=False).encode('utf-8')
