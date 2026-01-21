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
st.set_page_config(page_title="Ruvello Precision", page_icon="💎", layout="wide")

st.title("💎 Ruvello Global: Ultimate Measurement Sheet")
st.markdown("Generate **Zero-Overlap, 100% Calculated** Luxury Reports.")

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("1. Assets & Meta")
    
    # Auto-load logo logic
    default_logo = None
    if os.path.exists("logo.png"):
        default_logo = "logo.png"
        st.success("✅ Auto-loaded 'logo.png'!")
    
    uploaded_logo = st.file_uploader("Override Logo (Optional)", type=["png", "jpg", "jpeg"])
    final_logo_path = uploaded_logo if uploaded_logo else default_logo

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
    st.info("👇 **Allowance Logic:** Calculates Net Dimensions.")
    allowance_str = st.text_input("Allowance (e.g., -5 x 4)", value="-5 x 4")
    
    # NEW: Toggle to swap deduction logic
    swap_allowance = st.checkbox("🔄 Swap Deduction Order?", value=False, help="Check this if the first number should deduct from HEIGHT instead of LENGTH.")

# --- LOGIC: PARSE ALLOWANCE ---
def parse_allowance(allow_str, swap):
    nums = re.findall(r'\d+', allow_str)
    val1 = int(nums[0]) if len(nums) > 0 else 0
    val2 = int(nums[1]) if len(nums) > 1 else val1 # Use 1st val if 2nd missing
    
    if swap:
        return val1, val2 # 1st=Height, 2nd=Length
    else:
        return val2, val1 # 1st=Length, 2nd=Height (Default matching your PDF)

deduct_h, deduct_l = parse_allowance(allowance_str, swap_allowance)

# --- SECTION: DUAL COLUMN ENTRY ---
st.subheader("5. Precision Data Entry")
st.markdown("Copy **Gross Length** and **Gross Height** columns from Excel.")

paste_col1, paste_col2 = st.columns(2)
with paste_col1:
    raw_L = st.text_area("Paste GROSS LENGTHS Here", height=300, placeholder="287\n203")
with paste_col2:
    raw_H = st.text_area("Paste GROSS HEIGHTS Here", height=300, placeholder="83\n73")

# --- PROCESSING ENGINE ---
if st.button("⚡ Process & Calculate", type="primary"):
    if raw_L and raw_H:
        try:
            list_L = [float(x.strip()) for x in raw_L.split('\n') if x.strip()]
            list_H = [float(x.strip()) for x in raw_H.split('\n') if x.strip()]
            
            if len(list_L) != len(list_H):
                st.error(f"⚠️ Mismatch! Found {len(list_L)} Lengths but {len(list_H)} Heights.")
            else:
                df_new = pd.DataFrame({"GL": list_L, "GH": list_H})
                df_new["Slab No"] = [f"RG-{i+1}" for i in range(len(df_new))]
                
                # Deductions
                df_new["NL"] = df_new["GL"] - deduct_l
                df_new["NH"] = df_new["GH"] - deduct_h
                
                # --- PRECISION CALCULATION ---
                # 1. Calculate raw Area
                # 2. ROUND to 3 decimal places immediately (Standard Industry Practice)
                # This fixes the "Total" discrepancy vs Excel
                
                df_new["Gross Area"] = ((df_new["GL"] * df_new["GH"]) / 10000).round(3)
                df_new["Net Area"] = ((df_new["NL"] * df_new["NH"]) / 10000).round(3)
                
                st.session_state.smart_data = df_new
                st.success(f"✅ Calculated {len(df_new)} slabs with 3-decimal precision!")
        except ValueError:
            st.error("Error: Please ensure you pasted only Numbers.")

# --- DISPLAY DATA TABLE ---
if "smart_data" in st.session_state:
    final_df = st.session_state.smart_data
    
    # Summing the rounded values ensures 100% accuracy with the visible list
    total_gross = final_df["Gross Area"].sum()
    total_net = final_df["Net Area"].sum()
    total_count = len(final_df)
    
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Slabs", total_count)
    m2.metric("Gross Area", f"{total_gross:.3f} m2")
    m3.metric("Net Area", f"{total_net:.3f} m2")
    m4.metric("Deduction Applied", f"L -{deduct_l} | H -{deduct_h}")

    st.dataframe(final_df, use_container_width=True)
else:
    total_count = 0
    total_gross = 0
    total_net = 0
    final_df = pd.DataFrame()


# --- LUXURY PDF ENGINE (WHITE GLOVE) ---
def generate_smart_pdf(logo, material, inv, dt, thk, cont, mine, allow, data, t_slabs, t_gross, t_net):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=30, bottomMargin=30, leftMargin=30, rightMargin=30)
    elements = []
    
    # --- PALETTE (Chanel/Hermès Style) ---
    GOLD = HexColor('#C5A059')   
    BLACK = HexColor('#101010')  
    WHITE = HexColor('#FFFFFF')  
    DARK_GREY = HexColor('#303030')
    
    # --- STYLES ---
    styles = getSampleStyleSheet()
    
    # Typography
    style_co = ParagraphStyle('Co', fontName='Times-Bold', fontSize=26, textColor=BLACK, alignment=1, leading=30)
    style_addr = ParagraphStyle('Ad', fontName='Helvetica', fontSize=8, textColor=DARK_GREY, alignment=1, leading=12)
    style_sub = ParagraphStyle('Sub', fontName='Helvetica-Bold', fontSize=10, textColor=GOLD, alignment=1, letterSpacing=2)
    style_lbl = ParagraphStyle('Lbl', fontName='Helvetica-Bold', fontSize=7, textColor=HexColor('#555555'), textTransform='uppercase')
    
    # Table Headers
    style_th_main = ParagraphStyle('THm', fontName='Times-Bold', fontSize=10, textColor=GOLD, alignment=1)
    style_th_sub = ParagraphStyle('THs', fontName='Helvetica', fontSize=8, textColor=BLACK, alignment=1)
    
    # Cells
    style_td_id = ParagraphStyle('TDid', fontName='Helvetica', fontSize=9, textColor=BLACK, alignment=1)
    style_td_bold = ParagraphStyle('TDbold', fontName='Times-Bold', fontSize=10, textColor=BLACK, alignment=1)
    style_td_norm = ParagraphStyle('TDnorm', fontName='Times-Roman', fontSize=10, textColor=DARK_GREY, alignment=1)

    # 1. HEADER (Rigid Grid)
    header_rows = []
    
    if logo:
        if isinstance(logo, str):
            img = RLImage(logo, width=2.2*inch, height=1.6*inch, kind='proportional')
        else:
            logo.seek(0)
            img = RLImage(logo, width=2.2*inch, height=1.6*inch, kind='proportional')
        header_rows.append([img])
    
    header_rows.append([Paragraph("RUVELLO GLOBAL LLP", style_co)])
    
    addr_text = """1305, Uniyaro Ka Rasta, Chandpol Bazar, Jaipur, Rajasthan, INDIA - 302001<br/>
    Email: Rahul@ruvello.com | +91 9636648894"""
    header_rows.append([Paragraph(addr_text, style_addr)])
    
    header_rows.append([Paragraph(f"INSPECTION REPORT: {material.upper()}", style_sub)])
    
    t_layout = Table(header_rows, colWidths=[530])
    t_layout.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,1), (-1,1), 6),
        ('BOTTOMPADDING', (0,1), (-1,1), 4),
        ('TOPPADDING', (0,2), (-1,2), 4),
        ('BOTTOMPADDING', (0,2), (-1,2), 12),
    ]))
    elements.append(t_layout)
    
    # Gold Line Divider
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
        # Ensure 3-decimal formatting is maintained in display
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

    # Build Table
    t = Table(headers + rows, colWidths=col_widths, repeatRows=2)
    
    t.setStyle(TableStyle([
        # WHITE & GOLD THEME
        ('BACKGROUND', (0,0), (-1,0), WHITE),
        ('TEXTCOLOR', (0,0), (-1,0), GOLD),
        ('LINEBELOW', (0,0), (-1,0), 0.5, GOLD),
        
        ('BACKGROUND', (0,1), (-1,1), WHITE),
        ('TEXTCOLOR', (0,1), (-1,1), BLACK),
        ('LINEBELOW', (0,1), (-1,1), 1.5, GOLD),
        
        # Spans
        ('SPAN', (2,0), (4,0)),
        ('SPAN', (5,0), (7,0)),
        ('SPAN', (0,0), (0,1)),
        ('SPAN', (1,0), (1,1)),
        
        # Grid
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#EAEAEA')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        
        # Spacing
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        
        # Subtle Zebra
        ('ROWBACKGROUNDS', (2,0), (-2,-1), [WHITE, HexColor('#FAFAFA')]),
        
        # Total Row (Black & Gold Contrast)
        ('BACKGROUND', (0,-1), (-1,-1), BLACK),
        ('TEXTCOLOR', (0,-1), (-1,-1), GOLD),
        ('LINEABOVE', (0,-1), (-1,-1), 2, GOLD),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 40))

    # 4. SIGNATURE
    sig_data = [
        [Paragraph("Inspected By:", style_td_norm), Paragraph("For RUVELLO GLOBAL LLP:", style_td_norm)],
        [Spacer(1, 40), Spacer(1, 40)],
        [Paragraph("______________________", style_td_norm), Paragraph("______________________<br/><b>Authorized Signatory</b>", style_td_norm)]
    ]
    t_sig = Table(sig_data, colWidths=[200, 200])
    t_sig.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    elements.append(t_sig)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- BUTTON ---
st.markdown("---")
if st.button("✨ Generate Luxury Report", type="primary"):
    if total_count > 0:
        pdf = generate_smart_pdf(
            final_logo_path, material_name, invoice_no, date_val, thickness, 
            container_no, mine_name, allowance_str, final_df, total_count, total_gross, total_net
        )
        st.success(f"Generated PDF for {total_count} Slabs!")
        st.download_button("Download PDF 📥", data=pdf, file_name=f"Report_{material_name}.pdf", mime="application/pdf")
