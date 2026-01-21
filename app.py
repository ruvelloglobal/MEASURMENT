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
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Ruvello Smart Measurement", page_icon="💎", layout="wide")

st.title("💎 Ruvello Global: Precision Measurement App")
st.markdown("Generate **Ultra-Luxury** Packing Lists with **Dual-Column Smart Entry**.")

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("1. Assets & Meta")
    uploaded_logo = st.file_uploader("Upload Company Logo", type=["png", "jpg", "jpeg"])
    
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

# --- LOGIC: PARSE ALLOWANCE ---
# Rule: "-5 x 4" -> Deduct 5 from HEIGHT, Deduct 4 from LENGTH
def parse_allowance(allow_str):
    nums = re.findall(r'\d+', allow_str)
    if len(nums) >= 2:
        return int(nums[0]), int(nums[1]) # 1st=Height, 2nd=Length
    elif len(nums) == 1:
        return int(nums[0]), int(nums[0])
    else:
        return 0, 0

deduct_h, deduct_l = parse_allowance(allowance_str)

# --- SECTION: DUAL COLUMN ENTRY ---
st.subheader("5. Smart Data Entry (2 Columns)")
st.markdown("Copy the **Gross Length** column and **Gross Height** column separately from Excel.")

paste_col1, paste_col2 = st.columns(2)

with paste_col1:
    st.markdown("**Paste GROSS LENGTHS Here:**")
    raw_L = st.text_area("Column L", height=300, placeholder="280\n290\n300")

with paste_col2:
    st.markdown("**Paste GROSS HEIGHTS Here:**")
    raw_H = st.text_area("Column H", height=300, placeholder="180\n190\n200")

# --- PROCESSING ENGINE ---
if st.button("⚡ Process & Calculate", type="primary"):
    if raw_L and raw_H:
        try:
            # 1. Split and Clean Data
            list_L = [float(x.strip()) for x in raw_L.split('\n') if x.strip()]
            list_H = [float(x.strip()) for x in raw_H.split('\n') if x.strip()]
            
            # 2. Validation
            if len(list_L) != len(list_H):
                st.error(f"⚠️ Mismatch! Found {len(list_L)} Lengths but {len(list_H)} Heights. Please check your data.")
            else:
                # 3. Create DataFrame
                df_new = pd.DataFrame({
                    "GL": list_L,
                    "GH": list_H
                })
                
                # 4. Auto-Numbering
                df_new["Slab No"] = [f"RG-{i+1}" for i in range(len(df_new))]
                
                # 5. Smart Deduction (Net = Gross - Deduction)
                df_new["NL"] = df_new["GL"] - deduct_l
                df_new["NH"] = df_new["GH"] - deduct_h
                
                # 6. Area Calculation
                df_new["Gross Area"] = (df_new["GL"] * df_new["GH"]) / 10000
                df_new["Net Area"] = (df_new["NL"] * df_new["NH"]) / 10000
                
                # Save to Session
                st.session_state.smart_data = df_new
                st.success(f"✅ Successfully processed {len(df_new)} slabs!")
                
        except ValueError:
            st.error("Error: Please ensure you pasted only Numbers (no text headers).")
    else:
        st.warning("Please paste data into both columns.")

# --- DISPLAY DATA TABLE ---
if "smart_data" in st.session_state:
    final_df = st.session_state.smart_data
    
    # Totals
    total_gross = final_df["Gross Area"].sum()
    total_net = final_df["Net Area"].sum()
    total_count = len(final_df)
    
    # Metrics
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Slabs", total_count)
    m2.metric("Gross Area", f"{total_gross:.3f} m2")
    m3.metric("Net Area", f"{total_net:.3f} m2")
    m4.metric("Applied Deduction", f"H -{deduct_h} | L -{deduct_l}")

    # Preview
    st.markdown("### **Final Data Preview**")
    st.dataframe(
        final_df,
        column_order=["Slab No", "GL", "GH", "NL", "NH", "Gross Area", "Net Area"],
        column_config={
            "GL": st.column_config.NumberColumn("Gross L", format="%d"),
            "GH": st.column_config.NumberColumn("Gross H", format="%d"),
            "NL": st.column_config.NumberColumn("Net L", format="%d"),
            "NH": st.column_config.NumberColumn("Net H", format="%d"),
            "Gross Area": st.column_config.NumberColumn(format="%.3f"),
            "Net Area": st.column_config.NumberColumn(format="%.3f")
        },
        use_container_width=True
    )
else:
    total_count = 0
    total_gross = 0
    total_net = 0
    final_df = pd.DataFrame()


# --- LUXURY PDF ENGINE ---
def generate_smart_pdf(logo, material, inv, dt, thk, cont, mine, allow, data, t_slabs, t_gross, t_net):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20, bottomMargin=20, leftMargin=20, rightMargin=20)
    elements = []
    
    # --- PALETTE ---
    GOLD = HexColor('#C5A059')   
    BLACK = HexColor('#101010') 
    GREY = HexColor('#404040')
    HEADER_BG = HexColor('#000000') 
    SUB_HEADER_BG = HexColor('#252525')
    ZEBRA_EVEN = HexColor('#FFFFFF')
    ZEBRA_ODD = HexColor('#FAFAFA')

    # --- STYLES ---
    styles = getSampleStyleSheet()
    style_co = ParagraphStyle('Co', fontName='Times-Bold', fontSize=22, textColor=BLACK, alignment=1)
    style_sub = ParagraphStyle('Sub', fontName='Helvetica-Bold', fontSize=9, textColor=GOLD, alignment=1, letterSpacing=3)
    
    style_lbl = ParagraphStyle('Lbl', fontName='Helvetica-Bold', fontSize=7, textColor=GREY, textTransform='uppercase')
    
    style_th_gold = ParagraphStyle('THg', fontName='Times-Bold', fontSize=10, textColor=GOLD, alignment=1)
    style_th_wht = ParagraphStyle('THw', fontName='Helvetica', fontSize=8, textColor=colors.whitesmoke, alignment=1)
    
    style_td_id = ParagraphStyle('TDid', fontName='Helvetica', fontSize=9, textColor=BLACK, alignment=1)
    style_td_bold = ParagraphStyle('TDbold', fontName='Times-Bold', fontSize=10, textColor=BLACK, alignment=1)
    style_td_norm = ParagraphStyle('TDnorm', fontName='Times-Roman', fontSize=10, textColor=GREY, alignment=1)

    # 1. HEADER
    if logo:
        img = RLImage(logo, width=2.0*inch, height=1.5*inch, kind='proportional')
        img.hAlign = 'CENTER'
        elements.append(img)
    
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("RUVELLO GLOBAL LLP", style_co))
    elements.append(Paragraph(f"INSPECTION REPORT: {material.upper()}", style_sub))
    
    d = Drawing(500, 8)
    d.add(Line(0, 4, 550, 4, strokeColor=GOLD, strokeWidth=0.5))
    d.add(Line(0, 1, 550, 1, strokeColor=GOLD, strokeWidth=1.5))
    elements.append(d)
    elements.append(Spacer(1, 15))

    # 2. INFO GRID
    info_data = [
        [
            Paragraph(f"INVOICE NO:<br/><font size=10 color=black><b>{inv}</b></font>", style_lbl),
            Paragraph(f"DATE:<br/><font size=10 color=black><b>{dt.strftime('%d-%b-%Y')}</b></font>", style_lbl),
            Paragraph(f"TOTAL SLABS:<br/><font size=10 color=black><b>{t_slabs}</b></font>", style_lbl)
        ],
        [
            Paragraph(f"THICKNESS:<br/><font size=10 color=black><b>{thk}</b></font>", style_lbl),
            Paragraph(f"MINE / BLOCK:<br/><font size=10 color=black><b>{mine}</b></font>", style_lbl),
            Paragraph(f"CONTAINER / ALLOW:<br/><font size=10 color=black><b>{cont} ({allow})</b></font>", style_lbl)
        ]
    ]
    t_info = Table(info_data, colWidths=[180, 180, 180])
    t_info.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (-1,-1), HexColor('#FDFDFD')),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 20))

    # 3. MAIN TABLE
    col_widths = [35, 75, 50, 50, 65, 50, 50, 65]
    
    # Header Rows
    headers = [
        [
            Paragraph("S.NO", style_th_gold),
            Paragraph("SLAB NO", style_th_gold),
            Paragraph("GROSS MEASUREMENT", style_th_gold), "", "",
            Paragraph("NET MEASUREMENT", style_th_gold), "", ""
        ],
        [
            "", "",
            Paragraph("L (cm)", style_th_wht), Paragraph("H (cm)", style_th_wht), Paragraph("AREA (m2)", style_th_wht),
            Paragraph("L (cm)", style_th_wht), Paragraph("H (cm)", style_th_wht), Paragraph("AREA (m2)", style_th_wht)
        ]
    ]

    # Data Rows
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

    # Total Row
    total_row = [
        "", Paragraph("TOTAL", style_th_gold),
        "", "", Paragraph(f"<b>{t_gross:.3f}</b>", style_th_gold),
        "", "", Paragraph(f"<b>{t_net:.3f}</b>", style_th_gold),
    ]
    rows.append(total_row)

    # Build Table
    table_data = headers + rows
    t = Table(table_data, colWidths=col_widths, repeatRows=2)
    
    t.setStyle(TableStyle([
        # Headers
        ('BACKGROUND', (0,0), (-1,0), HEADER_BG),
        ('BACKGROUND', (0,1), (-1,1), SUB_HEADER_BG),
        ('SPAN', (2,0), (4,0)), # Span Gross
        ('SPAN', (5,0), (7,0)), # Span Net
        ('SPAN', (0,0), (0,1)), # Span S.No
        ('SPAN', (1,0), (1,1)), # Span Slab
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,1), 8),
        ('TOPPADDING', (0,0), (-1,1), 8),
        
        # Zebra Rows
        ('ROWBACKGROUNDS', (2,0), (-2,-1), [ZEBRA_EVEN, ZEBRA_ODD]),
        
        # Total Row
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
    t_sig = Table(sig_data, colWidths=[270, 270])
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
            uploaded_logo, material_name, invoice_no, date_val, thickness, 
            container_no, mine_name, allowance_str, final_df, total_count, total_gross, total_net
        )
        st.success(f"Generated PDF for {total_count} Slabs!")
        st.download_button("Download PDF 📥", data=pdf, file_name=f"Report_{material_name}.pdf", mime="application/pdf")
