"""
Recovery Instructions PDF Generator
Generates a well-formatted PDF with patient recovery instructions
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.platypus import ListFlowable, ListItem
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from io import BytesIO
from datetime import datetime


def generate_recovery_pdf(medical_guidance: dict, discharge_result: dict) -> bytes:
    """
    Generate a formatted PDF with recovery instructions

    Args:
        medical_guidance: Medical guidance data from Agent 8
        discharge_result: Complete discharge validation result

    Returns:
        PDF as bytes
    """

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=1*inch, bottomMargin=0.75*inch)

    # Container for PDF elements
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=12,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2ca02c'),
        spaceAfter=10,
        spaceBefore=15
    )

    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=colors.HexColor('#d62728'),
        spaceAfter=8,
        spaceBefore=10
    )

    normal_style = styles['Normal']
    normal_style.fontSize = 11
    normal_style.leading = 14

    # Title
    elements.append(Paragraph("Recovery Instructions", title_style))
    elements.append(Spacer(1, 0.2*inch))

    # Patient info (if available)
    discharge_summary = discharge_result.get('discharge_summary', {})

    # Get patient name (directly from discharge_summary top level)
    patient_name = discharge_summary.get('patient_name', 'Patient')

    # Get surgery/procedure name
    surgery_name = discharge_summary.get('procedure_performed', 'N/A')

    # Get discharge date (directly from discharge_summary top level)
    discharge_date = discharge_summary.get('discharge_date', 'N/A')

    gen_date = datetime.now().strftime("%B %d, %Y")

    patient_info_text = f"<b>Patient:</b> {patient_name}<br/><b>Surgery:</b> {surgery_name}<br/><b>Discharge Date:</b> {discharge_date}<br/><b>Generated:</b> {gen_date}"
    elements.append(Paragraph(patient_info_text, normal_style))
    elements.append(Spacer(1, 0.3*inch))

    # ===============================
    # 1. MEDICATIONS SCHEDULE
    # ===============================
    elements.append(Paragraph("💊 Medications Schedule", heading_style))

    med_schedule = medical_guidance['medication_schedule']
    elements.append(Paragraph(med_schedule['summary'], normal_style))
    elements.append(Spacer(1, 0.15*inch))

    # Medications table
    if med_schedule['detailed_schedule']:
        elements.append(Paragraph("<b>Your Medications:</b>", subheading_style))

        med_data = [['#', 'Medication', 'Dosage', 'Duration', 'Purpose']]

        for i, med in enumerate(med_schedule['detailed_schedule'], 1):
            med_data.append([
                Paragraph(str(i), normal_style),
                Paragraph(med['name'], normal_style),
                Paragraph(med['dosage'], normal_style),
                Paragraph(med['duration'], normal_style),
                Paragraph(med['purpose'], normal_style)
            ])

        med_table = Table(med_data, colWidths=[0.4*inch, 1.8*inch, 2*inch, 0.9*inch, 1.6*inch])
        med_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(med_table)
        elements.append(Spacer(1, 0.15*inch))

    # Key reminders
    if med_schedule['key_reminders']:
        elements.append(Paragraph("<b>⚠️ Important Reminders:</b>", subheading_style))
        reminder_items = [ListItem(Paragraph(reminder, normal_style)) for reminder in med_schedule['key_reminders']]
        elements.append(ListFlowable(reminder_items, bulletType='bullet'))
        elements.append(Spacer(1, 0.2*inch))

    # ===============================
    # 2. FOLLOW-UP APPOINTMENTS
    # ===============================
    elements.append(Paragraph("📅 Follow-up Appointments", heading_style))

    follow_up = medical_guidance['follow_up_plan']
    elements.append(Paragraph(follow_up['summary'], normal_style))
    elements.append(Spacer(1, 0.15*inch))

    # Appointments table
    if follow_up['appointments']:
        elements.append(Paragraph("<b>Scheduled Appointments:</b>", subheading_style))

        appt_data = [['#', 'When', 'Purpose']]

        for i, appt in enumerate(follow_up['appointments'], 1):
            timing = appt['timing']
            if appt.get('important'):
                timing += " [IMPORTANT]"
            appt_data.append([
                Paragraph(str(i), normal_style),
                Paragraph(timing, normal_style),
                Paragraph(appt['purpose'], normal_style)
            ])

        appt_table = Table(appt_data, colWidths=[0.4*inch, 2.8*inch, 3.5*inch])
        appt_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2196F3')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(appt_table)
        elements.append(Spacer(1, 0.15*inch))

    # What to bring
    if follow_up['what_to_bring']:
        elements.append(Paragraph("<b>What to Bring to Appointments:</b>", subheading_style))
        bring_items = [ListItem(Paragraph(item, normal_style)) for item in follow_up['what_to_bring']]
        elements.append(ListFlowable(bring_items, bulletType='bullet'))
        elements.append(Spacer(1, 0.2*inch))

    # ===============================
    # 3. ACTIVITY GUIDELINES
    # ===============================
    elements.append(Paragraph("🏃 Activity Guidelines", heading_style))

    activity = medical_guidance['activity_guidelines']
    elements.append(Paragraph(activity['summary'], normal_style))
    elements.append(Paragraph(f"<i>Duration: {activity['duration']}</i>", normal_style))
    elements.append(Spacer(1, 0.15*inch))

    # DO's and DON'Ts side by side
    do_dont_data = []

    # Header row
    do_dont_data.append([
        Paragraph("<b>✅ DO's</b>", subheading_style),
        Paragraph("<b>🚫 DON'Ts</b>", subheading_style)
    ])

    # Content rows - pair up items
    max_items = max(len(activity['dos']), len(activity['donts']))

    for i in range(max_items):
        do_text = activity['dos'][i] if i < len(activity['dos']) else ""
        dont_text = activity['donts'][i] if i < len(activity['donts']) else ""

        do_dont_data.append([
            Paragraph(f"• {do_text}", normal_style) if do_text else "",
            Paragraph(f"• {dont_text}", normal_style) if dont_text else ""
        ])

    do_dont_table = Table(do_dont_data, colWidths=[3.3*inch, 3.3*inch])
    do_dont_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#81C784')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#E57373')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))

    elements.append(do_dont_table)
    elements.append(Spacer(1, 0.2*inch))

    # ===============================
    # 4. WARNING SIGNS
    # ===============================
    elements.append(Paragraph("⚠️ Warning Signs - Call Doctor Immediately", heading_style))

    warning_signs = medical_guidance['warning_signs']
    elements.append(Paragraph(warning_signs['summary'], normal_style))
    elements.append(Spacer(1, 0.1*inch))

    # Warning signs in a highlighted box
    warning_data = [[Paragraph("<b>⚠️ URGENT - Call your doctor if you notice:</b>", normal_style)]]

    for sign in warning_signs['signs']:
        warning_data.append([Paragraph(f"• {sign}", normal_style)])

    warning_table = Table(warning_data, colWidths=[6.7*inch])
    warning_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#FFC107')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFF9C4')),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (0, 0), 12),
        ('GRID', (0, 0), (-1, -1), 2, colors.HexColor('#FF9800')),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))

    elements.append(warning_table)
    elements.append(Spacer(1, 0.2*inch))

    # ===============================
    # 5. RECOVERY TIMELINE
    # ===============================
    elements.append(Paragraph("🕐 Recovery Timeline", heading_style))
    timeline_text = medical_guidance['recovery_timeline']
    elements.append(Paragraph(timeline_text, normal_style))
    elements.append(Spacer(1, 0.3*inch))

    # ===============================
    # FOOTER / DISCLAIMER
    # ===============================
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_JUSTIFY
    )

    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("<b>IMPORTANT NOTES:</b>", subheading_style))
    disclaimer_text = """
    These instructions are extracted from your discharge summary. Follow them carefully for a smooth recovery.
    If you have any questions or concerns, contact your doctor immediately. Do not wait for your follow-up
    appointment if you notice any warning signs. Keep this document handy and bring it to all follow-up visits.
    """
    elements.append(Paragraph(disclaimer_text, disclaimer_style))

    # Build PDF
    doc.build(elements)

    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
