import streamlit as st
import pandas as pd
from datetime import date
from jinja2 import Template
from weasyprint import HTML
from num2words import num2words
import os

def format_bank_details(details):
    """Process bank details with bold headings"""
    lines = details.splitlines()
    formatted_lines = []
    for line in lines:
        if ':' in line:
            parts = line.split(":", 1)
            formatted_line = f"<strong>{parts[0].strip()}:</strong> {parts[1].strip()}"
            formatted_lines.append(formatted_line)
        else:
            formatted_lines.append(line)
    return "<br>".join(formatted_lines)

def get_company_data():
    """Fetch company data from Google Sheets"""
    sheet_id = "1tj__5HXGHKOgJBwtW8VhE0jeW4Us7h_OeO7rtNN4d64"
    sheet_name = "Sheet1"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(url, dtype=str).fillna("")
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error fetching company data: {e}")
        return None

def convert_to_words(amount, currency):
    """Convert numeric amount to words with currency handling"""
    raw_words = num2words(amount, to='currency', lang='en')
    
    replacements = {
        'USD': ('euro', 'dollar', 'Euros', 'Dollars'),
        'SAR': ('euro', 'riyal', 'Euros', 'Riyals')
    }
    
    for old, new in zip(replacements[currency][:2], replacements[currency][2:]):
        raw_words = raw_words.replace(old, new)
    
    return raw_words[0].upper() + raw_words[1:]

def generate_invoice_pdf(company_info, customer_ref, invoice_number, 
                         invoice_date, sar_rate, bank_details, items, invoice_currency):
    """Generate PDF invoice with currency handling"""
    if invoice_currency == "USD":
        total_usd = sum(item['qty'] * item['rate'] for item in items)
        total_sar = total_usd * sar_rate
        amount_words = convert_to_words(total_usd, 'USD')
    else:
        total_sar = sum(item['qty'] * item['rate'] for item in items)
        total_usd = None
        amount_words = convert_to_words(total_sar, 'SAR')

    formatted_bank_details = format_bank_details(bank_details)
    lme_used = any(item.get("lme_applied", False) for item in items)

    with open("invoice_template.html", "r", encoding="utf-8") as file:
        template = Template(file.read())

    html = template.render(
        company_info=company_info.replace("\n", "<br>"),
        customer_ref=customer_ref.replace("\n", "<br>"),
        invoice_number=invoice_number,
        invoice_date=invoice_date.strftime("%Y-%m-%d"),
        sar_rate=sar_rate,
        bank_details=formatted_bank_details,
        items=items,
        total_usd=total_usd,
        total_sar=total_sar,
        amount_words=amount_words,
        lme_used=lme_used,
        invoice_currency=invoice_currency
    )

    pdf_path = "invoice.pdf"
    HTML(string=html).write_pdf(pdf_path)
    return pdf_path

# Streamlit UI
st.title("Invoice Generator")

# Currency Selection
invoice_currency = st.radio("Invoice Currency", ["USD", "SAR"], horizontal=True)

# Company Data Section
company_data = get_company_data()
if company_data is not None:
    selected_company = st.selectbox("Select Company", company_data["Company Name"])
    company_address = company_data.loc[company_data["Company Name"] == selected_company, 
                                     "Company Address"].iloc[0]
    company_info = f"{selected_company}\n{company_address}"
else:
    company_info = st.text_area("Company Info", "Company Name\nAddress Line 1\nAddress Line 2")

# Invoice Details Section
col1, col2 = st.columns(2)
with col1:
    customer_ref = st.text_area("Customer Reference", 
                               "AGFZE/CU/TAT/---/2025\nCNTR: 1ST\nCONTAINER NO: YMLU3386328")
    invoice_number = st.text_input("Invoice Number", "30250124")
    
with col2:
    invoice_date = st.date_input("Invoice Date", date.today())
    if invoice_currency == "USD":
        sar_rate = st.number_input("Dollar to SAR Rate", value=3.7475, format="%.4f")
    else:
        sar_rate = 1.0  # Dummy value for template consistency

bank_details = st.text_area("Bank Details",
                           """BANK DETAILS: TABIB AL ARABIA FOR ENVIRONMENTAL SERVICES CO.
                           RIYAD BANK.
                           DOLLAR ACCOUNT A/C NO:3274336190440
                           IBAN NO:SA4920000003274336190440
                           BIN KHALDOON ST. BRANCH
                           SWIFT CODE:RIBLSARI""")

# Items Section
st.subheader("Items")
items = []
num_items = st.number_input("Number of Items", 1, 10, 1)

for i in range(num_items):
    with st.expander(f"Item {i+1}", expanded=True):
        desc = st.text_input(f"Description {i+1}", "Cu Birch Cliff Scrap", key=f"desc_{i}")
        qty = st.number_input(f"Quantity {i+1}", 0.0, 1000.0, 19.332, key=f"qty_{i}")
        
        lme_toggle = st.checkbox("Enable LME", key=f"lme_{i}")
        if lme_toggle:
            provision = st.number_input("Provision LME Value", 0.0, key=f"prov_{i}")
            lme_percent = st.slider("LME Percentage", 40.0, 100.0, 100.0, key=f"lme_pct_{i}")
            rate = provision * (lme_percent / 100)
        else:
            rate_label = f"Rate ({invoice_currency}) {i+1}"
            rate = st.number_input(rate_label, 0.0, value=8380.0, key=f"rate_{i}")
        
        items.append({
            "desc": desc,
            "qty": qty,
            "rate": rate,
            "lme_applied": lme_toggle,
            "lme_percentage": lme_percent if lme_toggle else None,
            "provision_lme_value": provision if lme_toggle else None
        })

# --- Generate and Download PDF ---
if st.button("Generate Invoice PDF"):
    pdf_file_path = generate_invoice_pdf(company_info, customer_ref, invoice_number, invoice_date, sar_rate, bank_details, items)
    if pdf_file_path and os.path.exists(pdf_file_path):
        with open(pdf_file_path, "rb") as f:
            st.download_button("Download Invoice", data=f.read(), file_name="invoice.pdf", mime="application/pdf")
