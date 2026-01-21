import streamlit as st
import pandas as pd
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
from PIL import Image

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Ruvello Measurement Sheet", page_icon="📏", layout="wide")

st.title("💎 Ruvello Global: Luxury Measurement Sheet")
st.markdown("Generate **Auto-Calculated, Multi-Page Inspection Reports** instantly.")

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
    allowance = st.text_input("Allowance", value="-5 x 4")

# --- MAGIC PASTE FUNCTIONALITY (New Feature) ---
with st.expander("🚀 **MAGIC PASTE FROM EXCEL (Click to Open)**", expanded=True):
    st.markdown("""
    **Instructions:**
    1. Open your Excel file.
    2. Select and Copy columns in this order: **[Slab No] [Gross L] [Gross H] [Net L] [Net H]**.
    3. Paste them into the box below and click 'Load Data'.
    *(Note: If you only have Gross dimensions, just paste 3 columns: Slab No, L, H)*
    """)
    
    paste_data = st.text_area("Paste Excel Data Here:", height=150, placeholder="RG-1\t280\t180\t275\t175\nRG-2\t290\t190\t285\t185")
    
    if st.button("⚡ Process Pasted Data", type="primary"):
        if paste_data:
            try:
                # Read tab-separated values (standard Excel copy format)
                # We assume no headers in the paste to keep it simple, or we skip bad rows
                data_io = io.StringIO(paste_data)
                
                # Attempt to parse
                pasted_df = pd.read_csv(data_io, sep="\t", header=None, on_bad_lines='skip')
                
                # Normalize Columns
                num_cols = pasted_df.shape[1]
                new_data = []

                for index, row in pasted_df.iterrows():
                    # clean data to ensure it's valid
                    try:
                        slab_no = str(row[0])
                        # Assuming structure: Col 0=Name, Col 1=GL, Col 2=GH, Col 3=NL, Col 4=NH
                        if num_cols >= 5:
                            gl = float(str(row[1]).replace(',', '').strip())
                            gh = float(str(row[2]).replace(',', '').strip())
                            nl = float(str(row[3]).replace(',', '').strip())
                            nh = float(str(row[4]).replace(',', '').strip())
                        elif num_cols >= 3:
                            # If only 3 cols, assume Net = Gross
                            gl = float(str(row[1]).replace(',', '').strip())
                            gh = float(str(row[2]).replace(',', '').strip())
                            nl = gl
                            nh = gh
                        else:
                            continue # Skip bad rows

                        new_data.append({
                            "Slab No": slab_no,
                            "Gross L (cm)": gl,
                            "Gross H (cm)": gh,
                            "Net L (cm)": nl,
                            "Net H (cm)": nh
                        })
                    except:
                        continue # Skip rows that aren't numbers (like headers)

                if new_data:
                    st.session_state.slab_data = pd.DataFrame(new_data)
                    st.success(f"Successfully loaded {len(new_data)} slabs!")
                else:
                    st.error("Could not parse data. Ensure you copied columns correctly.")
            except Exception as e:
                st.error(f"Error parsing data: {e}")

# --- MAIN DATA ENTRY ---
st.subheader("4. Slab Data Editor")

# Initialize Session State for Data if not exists
if "slab_data" not in st.session_state:
    st.session_state.slab_data = pd.DataFrame(
        [{"Slab No": f"RG-{i+1}", "Gross L (cm)": 0, "Gross H (cm)": 0, "Net L (cm)": 0, "Net H (cm)": 0} for i in range(5)]
    )

# Data Editor (Linked to Session State)
edited_df = st.data_editor(
    st.session_state.slab_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Gross L (cm)": st.column_config.NumberColumn(min_value=0, format="%d"),
        "Gross H (cm)": st.column_config.NumberColumn(min_value=0, format="%d"),
        "Net L (cm)": st.column_config.NumberColumn(min_value=0, format="%d"),
        "Net H (cm)": st.column_config.NumberColumn(min_value=0, format="%d"),
    }
)

# --- CALCULATIONS ---
# Formula: (L * H) / 10000 = Square Meters
calc_df = edited_df.copy()
# Ensure numeric conversion happens before calc
cols_to_numeric = ["Gross L (cm)", "Gross H (cm)", "Net L (cm)", "Net H (cm)"]
for col in cols_to_numeric:
    calc_df[col] = pd.to_numeric(calc_df[col], errors='coerce').fillna(0)

calc_df["Gross Area (m2)"] = (calc_df["Gross L (cm)"] * calc_df["Gross H (cm)"]) / 10000
calc_df["Net Area (m2)"] = (calc_df["Net L (cm)"] * calc_df["Net H (cm)"]) / 10000

# Filter out empty rows
final_data = calc_df[calc_df["Gross Area (m2)"] > 0].copy()
total_gross_area = final_data["Gross Area (m2)"].sum()
total_net_area = final_data["Net Area (m2)"].sum()
total_slabs = len(final_data)

# Show Totals
col1, col2, col3 = st.columns(3)
col1.metric("Total Slabs", f"{total_slabs}")
col2.metric("Total Gross Area", f"{total_gross_area:.3f} m2")
col3.metric("Total Net Area", f"{total_net_area:.3f} m2")


# --- PDF GENERATION ENGINE ---
def generate_measurement_pdf(logo, material, inv_no, date_v, thick, cont_no, mine, allow, data, t_slabs, t_gross, t_net):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20, bottomMargin=20, leftMargin=20, rightMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    # --- LUXURY COLORS ---
    GOLD = HexColor('#D4AF37')
    BLACK = HexColor('#000000')
    GREY = HexColor('#303030')
    LIGHT_BG = HexColor('#FAFAFA')

    # --- STYLES ---
    style_header = ParagraphStyle('Header', fontName='Times-Bold', fontSize=20, textColor=BLACK, alignment=1)
    style_sub = ParagraphStyle('Sub', fontName='Helvetica-Bold', fontSize=8, textColor=GOLD, alignment=1, letterSpacing=3)
    style_info_label = ParagraphStyle('InfoLbl', fontName='Helvetica-Bold', fontSize=7, textColor=GREY)
    style_info_val = ParagraphStyle('InfoVal', fontName='Helvetica-Bold', fontSize=9, textColor=BLACK)
    
    # Table Styles
    style_th_main = ParagraphStyle('TH', fontName='Times-Bold', fontSize=9, textColor=GOLD, alignment=1)
    style_th_sub = ParagraphStyle('THSub', fontName='Helvetica-Bold', fontSize=7, textColor=colors.whitesmoke, alignment=1)
    style_td = ParagraphStyle('TD', fontName='Helvetica', fontSize=9, textColor=BLACK, alignment=1)
    style_td_bold = ParagraphStyle('TDBold', fontName='Helvetica-Bold', fontSize=9, textColor=BLACK, alignment=1)

    # 1. HEADER LOGO & TITLE
    if logo:
        img = RLImage(logo, width=1.8*inch, height=1.4*inch, kind='proportional')
        img.hAlign = 'CENTER'
        elements.append(img)
    
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("RUVELLO GLOBAL LLP", style_header))
    elements.append(Paragraph(f"INSPECTION REPORT OF {material.upper()}", style_sub))
    
    # Gold Divider
    d = Drawing(500, 5)
    d.add(Line(0, 0, 550, 0, strokeColor=GOLD, strokeWidth=1))
    elements.append(d)
    elements.append(Spacer(1, 15))

    # 2. INFO BLOCK
    info_data = [
        [
            Paragraph(f"INVOICE NO:<br/><b>{inv_no}</b>", style_info_label),
            Paragraph(f"DATE:<br/><b>{date_v.strftime('%d-%b-%Y')}</b>", style_info_label),
            Paragraph(f"TOTAL SLABS:<br/><b>{t_slabs}</b>", style_info_label)
        ],
        [
            Paragraph(f"THICKNESS:<br/><b>{thick}</b>", style_info_label),
            Paragraph(f"MINE / BLOCK:<br/><b>{mine}</b>", style_info_label),
            Paragraph(f"CONTAINER NO:<br/><b>{cont_no}</b> ({allow})", style_info_label)
        ]
    ]
    
    t_info = Table(info_data, colWidths=[180, 180, 180])
    t_info.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 15))

    # 3. MEASUREMENT TABLE
    col_widths = [35, 75, 50, 50, 65, 50, 50, 65]

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
            Paragraph("L (cm)", style_th_sub), Paragraph("H (cm)", style_th_sub), Paragraph("AREA (m2)", style_th_sub),
        ]
    ]

    data_rows = []
    for index, row in data.iterrows():
        r = [
            Paragraph(str(index + 1), style_td),
            Paragraph(str(row["Slab No"]), style_td_bold),
            # Gross
            Paragraph(f"{row['Gross L (cm)']:.0f}", style_td),
            Paragraph(f"{row['Gross H (cm)']:.0f}", style_td),
            Paragraph(f"{row['Gross Area (m2)']:.3f}", style_td_bold),
            # Net
            Paragraph(f"{row['Net L (cm)']:.0f}", style_td),
            Paragraph(f"{row['Net H (cm)']:.0f}", style_td),
            Paragraph(f"{row['Net Area (m2)']:.3f}", style_td_bold),
        ]
        data_rows.append(r)

    total_row = [
        "", Paragraph("<b>TOTAL</b>", style_td_bold),
        "", "", Paragraph(f"<b>{t_gross:.3f}</b>", style_td_bold),
        "", "", Paragraph(f"<b>{t_net:.3f}</b>", style_td_bold),
    ]
    data_rows.append(total_row)

    full_table_data = headers + data_rows
    t_meas = Table(full_table_data, colWidths=col_widths, repeatRows=2)

    t_meas.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK), 
        ('BACKGROUND', (0,1), (-1,1), GREY),  
        ('TEXTCOLOR', (0,0), (-1,1), GOLD),   
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('SPAN', (2,0), (4,0)), 
        ('SPAN', (5,0), (7,0)), 
        ('SPAN', (0,0), (0,1)), 
        ('SPAN', (1,0), (1,1)), 
        ('ROWBACKGROUNDS', (2,0), (-2,-1), [colors.white, LIGHT_BG]),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('BACKGROUND', (0,-1), (-1,-1), GOLD), 
        ('TEXTCOLOR', (0,-1), (-1,-1), BLACK),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, BLACK),
    ]))
    
    elements.append(t_meas)
    elements.append(Spacer(1, 30))

    # 4. SIGNATURES
    sig_data = [
        [Paragraph("Inspected By:", style_td), Paragraph("Authorized Signatory:", style_td)],
        [Spacer(1, 40), Spacer(1, 40)],
        [Paragraph("_______________________", style_td), Paragraph("_______________________<br/><b>For RUVELLO GLOBAL LLP</b>", style_td)]
    ]
    t_sig = Table(sig_data, colWidths=[270, 270])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(t_sig)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- GENERATE BUTTON ---
st.markdown("---")
if st.button("✨ Generate Measurement Sheet", type="primary"):
    if total_slabs == 0:
        st.error("Please enter dimensions for at least one slab!")
    else:
        pdf_bytes = generate_measurement_pdf(
            uploaded_logo, material_name, invoice_no, date_val, thickness, 
            container_no, mine_name, allowance, final_data, total_slabs, total_gross_area, total_net_area
        )
        st.success(f"Generated Sheet for {total_slabs} Slabs!")
        st.download_button(
            label="Download PDF 📥",
            data=pdf_bytes,
            file_name=f"Measurement_{material_name}_{invoice_no}.pdf",
            mime="application/pdf"
        )
