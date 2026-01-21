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

st.title("💎 Ruvello Global: Smart Measurement Sheet")
st.markdown("Generate **1000% Accurate** Packing Lists with **Auto-Calculation Logic**.")

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
    st.header("4. Auto-Calculation Rules")
    st.info("👇 **Magic Rule:** Type the deduction rule below (e.g. `-5x4`). The app will auto-calculate Net dimensions.")
    allowance_str = st.text_input("Allowance (L x H)", value="-5 x 4")

# --- LOGIC: PARSE ALLOWANCE ---
# We extract numbers from the string "-5 x 4". 
# Assumes First Number = Length Deduction, Second Number = Height Deduction.
def parse_allowance(allow_str):
    # Find all digits in the string
    nums = re.findall(r'\d+', allow_str)
    if len(nums) >= 2:
        return int(nums[0]), int(nums[1])
    elif len(nums) == 1:
        return int(nums[0]), int(nums[0]) # Assume square if only 1 number
    else:
        return 0, 0

deduct_l, deduct_h = parse_allowance(allowance_str)

# --- SECTION: MAGIC PASTE ---
st.subheader("5. Smart Data Entry")
with st.expander("🚀 **PASTE EXCEL DATA (Gross L & Gross H Only)**", expanded=True):
    st.markdown("""
    **Instructions:**
    1. Copy **ONLY 2 Columns** from Excel: `[Gross Length]` and `[Gross Height]`.
    2. Paste them below. 
    3. The App will auto-generate Slab Numbers and Calculate Net Values based on your **Allowance Rule**.
    """)
    
    paste_data = st.text_area("Paste Data Here:", height=200, placeholder="280\t180\n290\t190\n300\t200")
    
    if paste_data:
        # Process the pasted text
        data_io = io.StringIO(paste_data)
        try:
            # Read 2 columns
            df_input = pd.read_csv(data_io, sep="\t", header=None, names=["GL", "GH"], on_bad_lines='skip')
            
            # Clean Data (ensure numbers)
            df_input["GL"] = pd.to_numeric(df_input["GL"], errors='coerce').fillna(0)
            df_input["GH"] = pd.to_numeric(df_input["GH"], errors='coerce').fillna(0)
            
            # Filter valid rows
            df_input = df_input[(df_input["GL"] > 0) & (df_input["GH"] > 0)].copy()
            
            # --- AUTO-CALCULATION ENGINE ---
            # 1. Generate Slab Numbers (RG-1, RG-2...)
            df_input["Slab No"] = [f"RG-{i+1}" for i in range(len(df_input))]
            
            # 2. Calculate Net Values using Allowance
            df_input["NL"] = df_input["GL"] - deduct_l
            df_input["NH"] = df_input["GH"] - deduct_h
            
            # 3. Calculate Areas
            df_input["Gross Area"] = (df_input["GL"] * df_input["GH"]) / 10000
            df_input["Net Area"] = (df_input["NL"] * df_input["NH"]) / 10000
            
            # Store in session state
            st.session_state.smart_data = df_input
            st.success(f"✅ Processed {len(df_input)} slabs! Applied Allowance: -{deduct_l} (L) x -{deduct_h} (H)")
            
        except Exception as e:
            st.error(f"Error parsing data: {e}")

# --- DISPLAY DATA TABLE ---
if "smart_data" in st.session_state:
    final_df = st.session_state.smart_data
    
    # Calculate Totals
    total_gross = final_df["Gross Area"].sum()
    total_net = final_df["Net Area"].sum()
    total_count = len(final_df)
    
    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Slabs", total_count)
    m2.metric("Gross Area", f"{total_gross:.3f} m2")
    m3.metric("Net Area", f"{total_net:.3f} m2")
    m4.metric("Active Allowance", f"-{deduct_l} x -{deduct_h}")

    # Editable Preview (In case you need to fix one specific slab)
    st.markdown("### **Data Preview (Editable)**")
    edited_final = st.data_editor(
        final_df,
        column_order=["Slab No", "GL", "GH", "NL", "NH", "Gross Area", "Net Area"],
        column_config={
            "GL": "Gross L", "GH": "Gross H",
            "NL": "Net L", "NH": "Net H",
            "Gross Area": st.column_config.NumberColumn(format="%.3f"),
            "Net Area": st.column_config.NumberColumn(format="%.3f")
        },
        use_container_width=True,
        num_rows="dynamic"
    )
else:
    total_count = 0
    total_gross = 0
    total_net = 0
    edited_final = pd.DataFrame()


# --- LUXURY PDF ENGINE ---
def generate_smart_pdf(logo, material, inv, dt, thk, cont, mine, allow, data, t_slabs, t_gross, t_net):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20, bottomMargin=20, leftMargin=20, rightMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    # --- COLOR PALETTE ---
    GOLD = HexColor('#C5A059')   # Rich Antique Gold
    BLACK = HexColor('#101010')  # Deep Black
    GREY = HexColor('#404040')
    TABLE_HEADER_BG = HexColor('#000000') 
    TABLE_SUB_BG = HexColor('#303030')
    ZEBRA_1 = HexColor('#FFFFFF')
    ZEBRA_2 = HexColor('#F9F9F9')

    # --- TEXT STYLES ---
    # Header
    style_company = ParagraphStyle('Co', fontName='Times-Bold', fontSize=22, textColor=BLACK, alignment=1, spaceAfter=2)
    style_title = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=9, textColor=GOLD, alignment=1, letterSpacing=3, spaceAfter=15)
    
    # Info Box
    style_lbl = ParagraphStyle('Lbl', fontName='Helvetica-Bold', fontSize=7, textColor=GREY, textTransform='uppercase')
    style_val = ParagraphStyle('Val', fontName='Times-Bold', fontSize=10, textColor=BLACK, leading=12)

    # Table
    style_th = ParagraphStyle('TH', fontName='Times-Bold', fontSize=10, textColor=GOLD, alignment=1)
    style_th_sub = ParagraphStyle('THs', fontName='Helvetica', fontSize=7, textColor=colors.whitesmoke, alignment=1)
    style_td_id = ParagraphStyle('TDid', fontName='Helvetica', fontSize=9, textColor=BLACK, alignment=1)
    style_td_bold = ParagraphStyle('TDbold', fontName='Times-Bold', fontSize=10, textColor=BLACK, alignment=1)
    style_td_norm = ParagraphStyle('TDnorm', fontName='Times-Roman', fontSize=10, textColor=GREY, alignment=1)

    # 1. HEADER
    if logo:
        img = RLImage(logo, width=2.0*inch, height=1.5*inch, kind='proportional')
        img.hAlign = 'CENTER'
        elements.append(img)
    
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("RUVELLO GLOBAL LLP", style_company))
    elements.append(Paragraph(f"INSPECTION REPORT: {material.upper()}", style_title))
    
    # Luxury Divider
    d = Drawing(500, 8)
    d.add(Line(0, 4, 550, 4, strokeColor=GOLD, strokeWidth=0.5))
    d.add(Line(0, 1, 550, 1, strokeColor=GOLD, strokeWidth=1.5))
    elements.append(d)
    elements.append(Spacer(1, 15))

    # 2. INFO GRID
    # We use a table for perfect alignment
    info_data = [
        [
            Paragraph(f"REF NO:<br/><font size=10 color=black><b>{inv}</b></font>", style_lbl),
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
        ('BACKGROUND', (0,0), (-1,-1), HexColor('#FCFCFC')),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 20))

    # 3. MAIN TABLE
    # Columns: S.No | Slab No | [Gross L | Gross H | Gross Area] | [Net L | Net H | Net Area]
    # Widths:  30   | 70      | 50      | 50      | 70         | 50    | 50    | 70
    col_widths = [35, 75, 50, 50, 65, 50, 50, 65]

    # Headers
    headers = [
        [
            Paragraph("S.NO", style_th),
            Paragraph("SLAB NO", style_th),
            Paragraph("GROSS MEASUREMENT", style_th), "", "",
            Paragraph("NET MEASUREMENT", style_th), "", ""
        ],
        [
            "", "",
            Paragraph("L (cm)", style_th_sub), Paragraph("H (cm)", style_th_sub), Paragraph("AREA (m2)", style_th_sub),
            Paragraph("L (cm)", style_th_sub), Paragraph("H (cm)", style_th_sub), Paragraph("AREA (m2)", style_th_sub)
        ]
    ]

    # Rows
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
        "", Paragraph("TOTAL", style_th),
        "", "", Paragraph(f"{t_gross:.3f}", style_th),
        "", "", Paragraph(f"{t_net:.3f}", style_th),
    ]
    rows.append(total_row)

    # Build
    table_data = headers + rows
    t = Table(table_data, colWidths=col_widths, repeatRows=2)
    
    t.setStyle(TableStyle([
        # Headers
        ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_BG),
        ('BACKGROUND', (0,1), (-1,1), TABLE_SUB_BG),
        ('SPAN', (2,0), (4,0)), # Span Gross
        ('SPAN', (5,0), (7,0)), # Span Net
        ('SPAN', (0,0), (0,1)), # Span S.No
        ('SPAN', (1,0), (1,1)), # Span Slab
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        
        # Zebra Rows
        ('ROWBACKGROUNDS', (2,0), (-2,-1), [ZEBRA_1, ZBRA_2]),
        
        # Total Row
        ('BACKGROUND', (0,-1), (-1,-1), GOLD),
        ('TEXTCOLOR', (0,-1), (-1,-1), BLACK),
        ('LINEABOVE', (0,-1), (-1,-1), 2, BLACK),
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
if st.button("✨ Generate PDF Report", type="primary"):
    if total_count > 0:
        pdf = generate_smart_pdf(
            uploaded_logo, material_name, invoice_no, date_val, thickness, 
            container_no, mine_name, allowance_str, edited_final, total_count, total_gross, total_net
        )
        st.success(f"Report Generated for {total_count} Slabs!")
        st.download_button("Download PDF 📥", data=pdf, file_name=f"Report_{material_name}.pdf", mime="application/pdf")
    else:
        st.error("No data found! Please paste Gross dimensions above.")
