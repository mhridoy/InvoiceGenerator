# app.py
import streamlit as st
import pandas as pd
from datetime import date
from jinja2 import Template
from weasyprint import HTML
from num2words import num2words
import os

def format_bank_details(details):
    """
    Process each line of the provided bank details:
    Bold the text before a colon and join the lines with HTML <br>.
    """
    lines = details.splitlines()
    formatted_lines = []
    for line in lines:
        if ':' in line:
            parts = line.split(":", 1)
            heading = parts[0].strip()
            content = parts[1].strip()
            formatted_line = f"<strong>{heading}:</strong> {content}" if content else f"<strong>{heading}:</strong>"
            formatted_lines.append(formatted_line)
        else:
            formatted_lines.append(line)
    return "<br>".join(formatted_lines)

def get_company_data():
    """
    Retrieve company data from a Google Sheet via CSV export.
    The sheet must contain "Company Name" and "Company Address" columns.
    """
    sheet_id = "1tj__5HXGHKOgJBwtW8VhE0jeW4Us7h_OeO7rtNN4d64"  # Replace if needed
    sheet_name = "Sheet1"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(url, dtype=str).fillna("")
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error fetching company data: {e}")
        return None

def generate_invoice_pdf(company_info, customer_ref, invoice_number, invoice_date, bank_details, items, invoice_currency, sar_rate=None):
    """
    Render the HTML invoice template and generate a PDF.

    • For a USD invoice:
      – Compute total USD from the items and apply the given sar_rate.
      – Convert the total USD into words (using num2words with currency formatting).

    • For a SAR invoice:
      – Compute the total SAR from the items.
      – Round the SAR amount to 2 decimals and then split the integer and fractional parts.
      – Convert the integer part to words normally, and then convert each digit of the decimal part.
    """
    # Determine if any item uses LME features
    lme_used = any(item.get("lme_applied", False) for item in items)

    if invoice_currency == "USD":
        total_usd = sum(item['qty'] * item['rate'] for item in items)
        total_sar = total_usd * sar_rate if sar_rate else 0.0
        # Convert USD total to words (replace Euro with Dollar)
        raw_words = num2words(total_usd, to='currency', lang='en')
        total_usd_words = raw_words.replace("euro", "dollar").replace("Euros", "Dollars")
        total_usd_words = total_usd_words[0].upper() + total_usd_words[1:]
        context = {
            "company_info": company_info,
            "customer_ref": customer_ref,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date.strftime("%Y-%m-%d"),
            "sar_rate": sar_rate,
            "bank_details": format_bank_details(bank_details),
            "items": items,
            "total_usd": total_usd,
            "total_sar": total_sar,
            "total_usd_words": total_usd_words,
            "lme_used": lme_used,
            "invoice_currency": invoice_currency
        }
    else:
        # For SAR invoice: no conversion rate is used.
        total_sar = sum(item['qty'] * item['rate'] for item in items)
        total_sar_rounded = round(total_sar, 2)
        total_sar_str = "{:.2f}".format(total_sar_rounded)
        integer_part, decimal_part = total_sar_str.split(".")
        integer_words = num2words(int(integer_part), lang='en')
        # Convert each digit in the decimal part individually to words
        decimal_words = " ".join(num2words(int(d), lang='en') for d in decimal_part)
        total_sar_words = (integer_words + " point " + decimal_words).capitalize()
        context = {
            "company_info": company_info,
            "customer_ref": customer_ref,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date.strftime("%Y-%m-%d"),
            "bank_details": format_bank_details(bank_details),
            "items": items,
            "total_sar": total_sar,
            "total_sar_words": total_sar_words,
            "lme_used": lme_used,
            "invoice_currency": invoice_currency
        }

    template_path = "invoice_template01.html"
    if not os.path.exists(template_path):
        st.error("Missing invoice_template01.html. Make sure it is in the same folder as app.py.")
        return None

    with open(template_path, "r", encoding="utf-8") as file:
        template_content = file.read()

    template = Template(template_content)
    rendered_html = template.render(**context)
    pdf_file_path = "invoice.pdf"
    HTML(string=rendered_html).write_pdf(pdf_file_path)
    return pdf_file_path

# --------------------- Streamlit Application --------------------- #

st.title("Invoice Generator")

# --- Select Invoice Type ---
invoice_currency = st.radio(
    "Choose Invoice Type",
    ("USD", "SAR"),
    index=0,
    key="invoice_type"
)

if invoice_currency == "USD":
    sar_rate_str = st.text_input("Dollar to SAR Rate", value="3.7475", key="sar_rate")
    try:
        sar_rate = float(sar_rate_str)
    except ValueError:
        st.error("Invalid SAR rate. Please enter a valid number.")
        sar_rate = 1.0
else:
    sar_rate = None  # Not needed for SAR invoice

# --- Company Data Section ---
st.subheader("Select Company Info from Google Sheets")
company_data = get_company_data()
if company_data is not None:
    st.dataframe(company_data)
    if "Company Name" in company_data.columns and "Company Address" in company_data.columns:
        companies = company_data["Company Name"].tolist()
        if companies:
            selected_company = st.selectbox("Select a Company", options=companies, key="company_selectbox")
            try:
                company_address = company_data.loc[company_data["Company Name"] == selected_company, "Company Address"].iloc[0]
            except IndexError:
                company_address = ""
            company_info_default = f"{selected_company}\n{company_address}"
        else:
            st.error("No companies available. Check your Google Sheet data.")
            company_info_default = "Enter company info manually."
    else:
        st.error("Required columns ('Company Name' and 'Company Address') not found.")
        company_info_default = "Enter company info manually."
else:
    company_info_default = "Enter company info manually."

company_info = st.text_area("Company Info (line by line)", value=company_info_default, key="company_info_text")

# --- Other Invoice Inputs ---
customer_ref = st.text_area(
    "Customer Reference (line by line)",
    "AGFZE/CU/TAT/---/2025\nCNTR: 1ST\nCONTAINER NO: YMLU3386328",
    key="customer_ref_text"
)
invoice_number = st.text_input("Invoice Number", "30250124")
invoice_date = st.date_input("Invoice Date", date.today(), key="invoice_date")

bank_details = st.text_area(
    "Bank Details (line by line)",
    """BANK DETAILS: TABIB AL ARABIA FOR ENVIRONMENTAL SERVICES CO.
RIYAD BANK.
DOLLAR ACCOUNT A/C NO:3274336190440
IBAN NO:SA4920000003274336190440
BIN KHALDOON ST. BRANCH
SWIFT CODE:RIBLSARI""",
    key="bank_details_text"
)

# --- Invoice Items Section ---
st.subheader("Items")
items = []
num_items = st.number_input("Number of Items", min_value=1, value=1, step=1, key="num_items")
for i in range(num_items):
    with st.expander(f"Item {i+1}"):
        desc = st.text_input(f"Description {i+1}", "Cu Birch Cliff Scrap", key=f"desc_{i}")
        qty = st.number_input(f"Quantity {i+1}", value=19.332, step=0.001, key=f"qty_{i}")

        # LME toggle: if enabled ask for LME details; otherwise, use a base rate.
        lme_toggle = st.checkbox("Enable LME for this item?", key=f"lme_toggle_{i}")
        if lme_toggle:
            provision_lme_value = st.number_input("Provision LME Value", value=0.00, step=0.01, key=f"provision_lme_value_{i}")
            lme_percentage = st.slider("LME Percentage (40.00% - 100.00%)",
                                       min_value=40.00, max_value=100.00, value=100.00, step=0.01, format="%.2f", key=f"lme_percentage_{i}")
            final_rate = provision_lme_value * (lme_percentage / 100.0)
        else:
            provision_lme_value = None
            lme_percentage = None
            if invoice_currency == "USD":
                final_rate = st.number_input(f"Base Rate (USD) {i+1}", value=8380.00, step=0.01, key=f"base_rate_{i}")
            else:
                final_rate = st.number_input(f"Base Rate (SAR) {i+1}", value=8380.00, step=0.01, key=f"base_rate_{i}")

        items.append({
            "desc": desc,
            "qty": qty,
            "rate": final_rate,
            "lme_applied": lme_toggle,
            "lme_percentage": lme_percentage,
            "provision_lme_value": provision_lme_value
        })

# --- Generate and Download PDF ---
if st.button("Generate Invoice PDF"):
    pdf_file_path = generate_invoice_pdf(company_info, customer_ref, invoice_number, invoice_date, bank_details, items, invoice_currency, sar_rate)
    if pdf_file_path and os.path.exists(pdf_file_path):
        with open(pdf_file_path, "rb") as f:
            st.download_button("Download Invoice", data=f.read(), file_name="invoice.pdf", mime="application/pdf")
