import streamlit as st
import pandas as pd
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.graphics.shapes import Drawing, Line
import io
import os
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Ruvello Measurement", page_icon="💎", layout="wide")

st.title("💎 Ruvello Global: Ultimate Measurement Sheet")
st.markdown("Generate **Signed, Sealed, Luxury** Inspection Reports.")

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("1. Assets (Auto-Load)")
    
    # 1. LOGO LOGIC
    default_logo = "logo.png" if os.path.exists("logo.png") else None
    uploaded_logo = st.file_uploader("Upload Logo (Optional)", type=["png", "jpg", "jpeg"])
    final_logo_path = uploaded_logo if uploaded_logo else default_logo
    if default_logo and not uploaded_logo:
        st.success("✅ 'logo.png' loaded.")

    # 2. SIGNATURE LOGIC
    default_sig = "signature.png" if os.path.exists("signature.png") else None
    uploaded_sig = st.file_uploader("Upload Signature (Optional)", type=["png", "jpg", "jpeg"])
    final_sig_path = uploaded_sig if uploaded_sig else default_sig
    if default_sig and not uploaded_sig:
        st.success("✅ 'signature.png' loaded.")

    st.header("2. Report Details")
    material_name = st.text_input("Material Name", value="ABSOLUTE BLACK")
    invoice_no = st.text_input("Invoice / Ref No", value="EXP/2026/001")
    date_val = st.date_input("Inspection Date", value=datetime.today())
    
    st.header("3. Block & Logistics")
    thickness = st.text_input("Thickness", value="16MM")
    container_no = st.text_input("Container No.", value="TGHU 1234567")
    mine_name = st.text_input("Mine / Block No.", value="KODAD")
    
    st.markdown("---")
    st.header("4. Deduction Rules")
    st.info("👇 **Rule:** First number deducts from **Height**, Second from **Length**.")
    allowance_str = st.text_input("Allowance (H x L)", value="-5 x 4")
    swap_allowance = st.checkbox("🔄 Swap Deduction Order?", value=False)

# --- LOGIC: PARSE ALLOWANCE ---
def parse_allowance(allow_str, swap):
    nums = re.findall(r'\d+', allow_str)
    val1 = int(nums[0]) if len(nums) > 0 else 0
    val2 = int(nums[1]) if len(nums) > 1 else val1
    return (val1, val2) if swap else (val2, val1)

deduct_h, deduct_l = parse_allowance(allowance_str, swap_allowance)

# --- SECTION: DUAL COLUMN ENTRY ---
st.subheader("5. Precision Data Entry")
col1, col2 = st.columns(2)
with col1:
    raw_L = st.text_area("Paste GROSS LENGTHS", height=300, placeholder="287\n203")
with col2:
    raw_H = st.text_area("Paste GROSS HEIGHTS", height=300, placeholder="83\n73")

# --- PROCESSING ENGINE ---
if st.button("⚡ Process & Calculate", type="primary"):
    if raw_L and raw_H:
        try:
            list_L = [float(x.strip()) for x in raw_L.split('\n') if x.strip()]
            list_H = [float(x.strip()) for x in raw_H.split('\n') if x.strip()]
            
            if len(list_L) != len(list_H):
                st.error(f"⚠️ Mismatch! Lengths: {len(list_L)}, Heights: {len(list_H)}")
            else:
                df = pd.DataFrame({"GL": list_L, "GH": list_H})
                df["Slab No"] = [f"RG-{i+1}" for i in range(len(df))]
                df["NL"] = df["GL"] - deduct_l
                df["NH"] = df["GH"] - deduct_h
                df["Gross Area"] = ((df["GL"] * df["GH"]) / 10000).round(3)
                df["Net Area"] = ((df["NL"] * df["NH"]) / 10000).round(3)
                
                st.session_state.smart_data = df
                st.success(f"✅ Calculated {len(df)} slabs!")
        except ValueError:
            st.error("Error: Numbers only please.")

# --- DISPLAY TABLE ---
if "smart_data" in st.session_state:
    final_df = st.session_state.smart_data
    t_gross = final_df["Gross Area"].sum()
    t_net = final_df["Net Area"].sum()
    t_count = len(final_df)
    
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Slabs", t_count)
    c2.metric("Gross Area", f"{t_gross:.3f} m2")
    c3.metric("Net Area", f"{t_net:.3f} m2")
    c4.metric("Deduction", f"L -{deduct_l} | H -{deduct_h}")
    st.dataframe(final_df, use_container_width=True)
else:
    t_count, t_gross, t_net = 0, 0, 0
    final_df = pd.DataFrame()


# --- LUXURY PDF ENGINE ---
def generate_smart_pdf(logo, sig, material, inv, dt, thk, cont, mine, allow, data, t_slabs, t_gross, t_net):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=30, bottomMargin=30, leftMargin=30, rightMargin=30)
    elements = []
    
    # --- PALETTE ---
    GOLD = HexColor('#C5A059')   
    BLACK = HexColor('#101010')  
    WHITE = HexColor('#FFFFFF')  
    DARK_GREY = HexColor('#303030')
    
    # --- STYLES ---
    styles = getSampleStyleSheet()
    style_co = ParagraphStyle('Co', fontName='Times-Bold', fontSize=26, textColor=BLACK, alignment=1, leading=30)
    style_addr = ParagraphStyle('Ad', fontName='Helvetica', fontSize=8, textColor=DARK_GREY, alignment=1, leading=12)
    style_sub = ParagraphStyle('Sub', fontName='Helvetica-Bold', fontSize=10, textColor=GOLD, alignment=1, letterSpacing=2)
    style_lbl = ParagraphStyle('Lbl', fontName='Helvetica-Bold', fontSize=7, textColor=HexColor('#555555'), textTransform='uppercase')
    
    # Table Styles
    style_th_main = ParagraphStyle('THm', fontName='Times-Bold', fontSize=10, textColor=GOLD, alignment=1)
    style_th_sub = ParagraphStyle('THs', fontName='Helvetica', fontSize=8, textColor=BLACK, alignment=1)
    style_td_id = ParagraphStyle('TDid', fontName='Helvetica', fontSize=9, textColor=BLACK, alignment=1)
    style_td_bold = ParagraphStyle('TDbold', fontName='Times-Bold', fontSize=10, textColor=BLACK, alignment=1)
    style_td_norm = ParagraphStyle('TDnorm', fontName='Times-Roman', fontSize=10, textColor=DARK_GREY, alignment=1)

    # 1. HEADER
    header_rows = []
    if logo:
        logo_obj = logo if isinstance(logo, str) else (logo.seek(0) or logo)
        img = RLImage(logo_obj, width=2.2*inch, height=1.6*inch, kind='proportional')
        header_rows.append([img])
    
    header_rows.append([Paragraph("RUVELLO GLOBAL LLP", style_co)])
    
    # UPDATED EMAIL ORDER
    addr_text = """1305, Uniyaro Ka Rasta, Chandpol Bazar, Jaipur, Rajasthan, INDIA - 302001<br/>
    Email: ruvelloglobal@gmail.com | Rahul@ruvello.com | +91 9636648894"""
    header_rows.append([Paragraph(addr_text, style_addr)])
    
    header_rows.append([Paragraph(f"INSPECTION REPORT: {material.upper()}", style_sub)])
    
    t_layout = Table(header_rows, colWidths=[530])
    t_layout.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,2), (-1,2), 12),
    ]))
    elements.append(t_layout)
    
    d = Drawing(500, 5)
    d.add(Line(0, 0, 535, 0, strokeColor=GOLD, strokeWidth=1.5))
    elements.append(d)
    elements.append(Spacer(1, 20))

    # 2. INFO GRID
    row1 = [
        Paragraph(f"REF NO:<br/><font size=10><b>{inv}</b></font>", style_lbl),
        Paragraph(f"DATE:<br/><font size=10><b>{dt.strftime('%d-%b-%Y')}</b></font>", style_lbl),
        Paragraph(f"TOTAL SLABS:<br/><font size=10><b>{t_slabs}</b></font>", style_lbl),
        Paragraph(f"MINE / BLOCK:<br/><font size=10><b>{mine}</b></font>", style_lbl)
    ]
    row2 = [
        Paragraph(f"THICKNESS:<br/><font size=10><b>{thk}</b></font>", style_lbl),
        Paragraph(f"CONTAINER NO:<br/><font size=10><b>{cont}</b></font>", style_lbl),
        Paragraph(f"ALLOWANCE:<br/><font size=10><b>{allow}</b></font>", style_lbl),
        Paragraph("", style_lbl)
    ]
    
    t_info = Table([row1, row2], colWidths=[133, 133, 133, 133])
    t_info.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#E0E0E0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 12),
        ('BACKGROUND', (0,0), (-1,-1), HexColor('#FAFAFA')),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 25))

    # 3. MAIN TABLE
    col_widths = [40, 80, 60, 60, 75, 60, 60, 75]
    
    headers = [
        [
            Paragraph("S.NO", style_th_main),
            Paragraph("SLAB NO", style_th_main),
            Paragraph("GROSS MEASUREMENT", style_th_main), "", "",
            Paragraph("NET MEASUREMENT", style_th_main), "", ""
        ],
        [
            "", "",
            Paragraph("L (cm)", style_th_sub), Paragraph("H (cm)", style_th_sub), Paragraph("AREA (m2)", style_th_sub),
            Paragraph("L (cm)", style_th_sub), Paragraph("H (cm)", style_th_sub), Paragraph("AREA (m2)", style_th_sub)
        ]
    ]

    rows = []
    for i, row in data.iterrows():
        r = [
            Paragraph(str(i+1), style_td_id),
            Paragraph(str(row["Slab No"]), style_td_bold),
            Paragraph(f"{row['GL']:.0f}", style_td_norm),
            Paragraph(f"{row['GH']:.0f}", style_td_norm),
            Paragraph(f"<b>{row['Gross Area']:.3f}</b>", style_td_norm),
            Paragraph(f"{row['NL']:.0f}", style_td_norm),
            Paragraph(f"{row['NH']:.0f}", style_td_norm),
            Paragraph(f"<b>{row['Net Area']:.3f}</b>", style_td_bold),
        ]
        rows.append(r)

    total_row = [
        "", Paragraph("TOTAL", style_th_main),
        "", "", Paragraph(f"<b>{t_gross:.3f}</b>", style_th_main),
        "", "", Paragraph(f"<b>{t_net:.3f}</b>", style_th_main),
    ]
    rows.append(total_row)

    t = Table(headers + rows, colWidths=col_widths, repeatRows=2)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), WHITE),
        ('TEXTCOLOR', (0,0), (-1,0), GOLD),
        ('LINEBELOW', (0,0), (-1,0), 0.5, GOLD),
        ('BACKGROUND', (0,1), (-1,1), WHITE),
        ('TEXTCOLOR', (0,1), (-1,1), BLACK),
        ('LINEBELOW', (0,1), (-1,1), 1.5, GOLD),
        ('SPAN', (2,0), (4,0)), ('SPAN', (5,0), (7,0)),
        ('SPAN', (0,0), (0,1)), ('SPAN', (1,0), (1,1)),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#DDDDDD')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (2,0), (-2,-1), [WHITE, HexColor('#FAFAFA')]),
        ('BACKGROUND', (0,-1), (-1,-1), BLACK),
        ('TEXTCOLOR', (0,-1), (-1,-1), GOLD),
        ('LINEABOVE', (0,-1), (-1,-1), 2, GOLD),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 40))

    # 4. SIGNATURE (Aligned Right, No "Inspected By")
    sig_content = []
    sig_content.append(Paragraph("For RUVELLO GLOBAL LLP", style_td_norm))
    sig_content.append(Spacer(1, 10))
    
    if sig:
        sig_obj = sig if isinstance(sig, str) else (sig.seek(0) or sig)
        # Assuming signature is ~2 inch wide
        img_sig = RLImage(sig_obj, width=2.0*inch, height=0.8*inch, kind='proportional')
        img_sig.hAlign = 'CENTER'
        sig_content.append(img_sig)
    else:
        sig_content.append(Spacer(1, 40)) # Space for manual sign if no file
        
    sig_content.append(Paragraph("__________________________", style_td_norm))
    sig_content.append(Paragraph("<b>Authorized Signatory</b>", style_td_norm))
    
    # Table to push it to the right
    t_sig = Table([[ "", [item for item in sig_content] ]], colWidths=[300, 230])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('VALIGN', (1,0), (1,0), 'BOTTOM'),
    ]))
    elements.append(t_sig)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- BUTTON ---
st.markdown("---")
if st.button("✨ Generate Luxury Report", type="primary"):
    if t_count > 0:
        pdf = generate_smart_pdf(
            final_logo_path, final_sig_path, material_name, invoice_no, date_val, thickness, 
            container_no, mine_name, allowance_str, final_df, t_count, t_gross, t_net
        )
        st.success(f"Generated PDF for {t_count} Slabs!")
        st.download_button("Download PDF 📥", data=pdf, file_name=f"Report_{material_name}.pdf", mime="application/pdf")
