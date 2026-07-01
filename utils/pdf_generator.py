# utils/pdf_generator.py — PDF Challan Generator using ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable)
from io import BytesIO
from datetime import datetime

# ── Colour palette ──
NAVY  = colors.HexColor('#1F4E79')
BLUE  = colors.HexColor('#2E75B6')
LGRAY = colors.HexColor('#F2F2F2')
RED   = colors.HexColor('#C0392B')
WHITE = colors.white
BLACK = colors.black


def generate_challan_pdf(challan_data: dict) -> BytesIO:
    """
    Generate a professional PDF challan.

    Required keys in challan_data:
        challan_number, issue_date, due_date,
        vehicle_reg, vehicle_model,
        owner_name, owner_cnic,
        violation_type, violation_date, location,
        fine_amount, penalty, total_due,
        officer_name, badge_number
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
        title=f"Traffic Challan {challan_data.get('challan_number', '')}",
    )

    styles = getSampleStyleSheet()
    W      = doc.width   # usable page width

    # ── Custom paragraph styles ──
    def make_style(name, **kwargs):
        return ParagraphStyle(name, parent=styles['Normal'], **kwargs)

    h_white   = make_style('hw', fontSize=18, alignment=TA_CENTER,
                            textColor=WHITE, fontName='Helvetica-Bold')
    sub_white = make_style('sw', fontSize=10, alignment=TA_CENTER,
                            textColor=WHITE, fontName='Helvetica')
    label_st  = make_style('lbl', fontSize=10, fontName='Helvetica-Bold', textColor=BLACK)
    value_st  = make_style('val', fontSize=10, fontName='Helvetica', textColor=BLACK)
    center_st = make_style('ctr', fontSize=10, alignment=TA_CENTER, fontName='Helvetica')
    right_st  = make_style('rgt', fontSize=10, alignment=TA_RIGHT, fontName='Helvetica')
    fine_st   = make_style('fin', fontSize=11, fontName='Helvetica', textColor=BLACK)
    total_st  = make_style('tot', fontSize=13, fontName='Helvetica-Bold', textColor=RED)
    foot_st   = make_style('fot', fontSize=8, alignment=TA_CENTER,
                            textColor=colors.grey, fontName='Helvetica-Oblique')

    story = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  HEADER BLOCK
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    header_data = [
        [Paragraph('METROPOLITAN TRAFFIC AUTHORITY', h_white)],
        [Paragraph('DIGITAL TRAFFIC CHALLAN', sub_white)],
        [Paragraph('Official Notice of Traffic Violation', sub_white)],
    ]
    header_tbl = Table(header_data, colWidths=[W])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), NAVY),
        ('TOPPADDING',    (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── Challan ID + issue date row ──
    cn_data = [[
        Paragraph(f"<b>Challan No:  {challan_data.get('challan_number', 'N/A')}</b>",
                  make_style('cn', fontSize=13, fontName='Helvetica-Bold', textColor=NAVY)),
        Paragraph(f"Issue Date: {challan_data.get('issue_date', 'N/A')}",
                  make_style('id', fontSize=10, alignment=TA_RIGHT, fontName='Helvetica')),
    ]]
    cn_tbl = Table(cn_data, colWidths=[W * 0.6, W * 0.4])
    cn_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), LGRAY),
        ('BOX',           (0, 0), (-1, -1), 1.5, BLUE),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
    ]))
    story.append(cn_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ─── Helper: Section header bar ───────────────────────────
    def section_bar(title: str):
        sh_style = make_style('sh', fontSize=11, fontName='Helvetica-Bold',
                               textColor=WHITE)
        t = Table([[Paragraph(title, sh_style)]], colWidths=[W])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), BLUE),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ]))
        return t

    # ─── Helper: Two-column info table ────────────────────────
    def info_tbl(rows):
        data = [[Paragraph(r[0], label_st), Paragraph(str(r[1]), value_st)]
                for r in rows]
        t = Table(data, colWidths=[W * 0.35, W * 0.65])
        t.setStyle(TableStyle([
            ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [WHITE, LGRAY]),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ]))
        return t

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  VEHICLE & OWNER INFORMATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    story.append(section_bar('VEHICLE & OWNER INFORMATION'))
    story.append(info_tbl([
        ('Registration No:',    challan_data.get('vehicle_reg', 'N/A')),
        ('Vehicle:',            challan_data.get('vehicle_model', 'N/A')),
        ('Owner Name:',         challan_data.get('owner_name', 'N/A')),
        ('Owner CNIC:',         challan_data.get('owner_cnic', 'N/A')),
    ]))
    story.append(Spacer(1, 0.3*cm))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  VIOLATION DETAILS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    story.append(section_bar('VIOLATION DETAILS'))
    story.append(info_tbl([
        ('Violation Type:',  challan_data.get('violation_type', 'N/A')),
        ('Date & Time:',     challan_data.get('violation_date', 'N/A')),
        ('Location:',        challan_data.get('location', 'N/A')),
        ('Issuing Officer:', challan_data.get('officer_name', 'N/A')),
        ('Badge Number:',    challan_data.get('badge_number', 'N/A')),
    ]))
    story.append(Spacer(1, 0.3*cm))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  FINE SUMMARY
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    story.append(section_bar('FINE SUMMARY'))
    fine_amount = challan_data.get('fine_amount', 0)
    penalty     = challan_data.get('penalty', 0)
    total_due   = challan_data.get('total_due', fine_amount)
    due_date    = challan_data.get('due_date', 'N/A')

    fine_data = [
        [Paragraph('Base Fine:',     fine_st), Paragraph(f'PKR {fine_amount:,.2f}', fine_st)],
        [Paragraph('Late Penalty:',  fine_st), Paragraph(f'PKR {penalty:,.2f}',     fine_st)],
        [Paragraph('TOTAL AMOUNT DUE:', total_st), Paragraph(f'PKR {total_due:,.2f}', total_st)],
        [Paragraph('Payment Due Date:', label_st), Paragraph(str(due_date), value_st)],
    ]
    fine_tbl = Table(fine_data, colWidths=[W * 0.45, W * 0.55])
    fine_tbl.setStyle(TableStyle([
        ('GRID',           (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 0), (-1, 1),  [WHITE, LGRAY]),
        ('BACKGROUND',     (0, 2), (-1, 2),  colors.HexColor('#FDECEA')),
        ('TOPPADDING',     (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 8),
        ('LEFTPADDING',    (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',   (0, 0), (-1, -1), 10),
    ]))
    story.append(fine_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  PAYMENT INSTRUCTIONS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    story.append(section_bar('PAYMENT INSTRUCTIONS'))
    instructions = (
        '<b>Payment Methods Accepted:</b><br/>'
        '1. <b>Cash</b> — at any Traffic Authority office, counter hours 9am–5pm Mon–Sat.<br/>'
        '2. <b>Bank Transfer</b> — Account: 1234-567-8901234 | Bank: National Bank of Pakistan.<br/>'
        '3. <b>Online</b> — visit traffic.gov.pk, enter your Challan Number to pay online.<br/><br/>'
        '<b>Important:</b> Fines not paid within 15 days attract a 10% late surcharge per week '
        '(maximum 50%). Present this challan (printed or digital) at time of payment. '
        'Keep your payment receipt. Failure to pay may result in vehicle immobilisation.'
    )
    story.append(Paragraph(
        instructions,
        make_style('inst', fontSize=9, fontName='Helvetica', leading=14,
                   leftIndent=5, rightIndent=5, spaceBefore=6, spaceAfter=6)
    ))
    story.append(Spacer(1, 0.5*cm))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  SIGNATURE AREA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    sig_data = [
        [Paragraph('Issuing Officer', center_st),
         Paragraph('Receiving Officer', center_st)],
        [Paragraph('<br/><br/><br/>_________________________', center_st),
         Paragraph('<br/><br/><br/>_________________________', center_st)],
        [Paragraph(challan_data.get('officer_name', ''), center_st),
         Paragraph('', center_st)],
        [Paragraph(f"Badge: {challan_data.get('badge_number', '')}", center_st),
         Paragraph('Date: ______________', right_st)],
    ]
    sig_tbl = Table(sig_data, colWidths=[W / 2, W / 2])
    sig_tbl.setStyle(TableStyle([
        ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING',     (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  FOOTER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    story.append(HRFlowable(width=W, thickness=1, color=NAVY))
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    footer_text = (
        f"Computer-generated challan | "
        f"Challan No: {challan_data.get('challan_number', 'N/A')} | "
        f"Generated: {gen_time} | "
        f"Metropolitan Traffic Authority"
    )
    story.append(Paragraph(footer_text, foot_st))

    doc.build(story)
    buffer.seek(0)
    return buffer
