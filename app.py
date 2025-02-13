import streamlit as st
import pandas as pd
from datetime import date
from jinja2 import Template
from weasyprint import HTML

def get_company_data():
    """
    Fetch company data from a public Google Sheet.
    The sheet is identified by its sheet_id and sheet_name.
    The URL returns CSV data which is read by pandas.
    """
    sheet_id = "1MyF5yRHgvu1JqqJljTQSo6GDhvpPcezU_aSrXYd90aM"
    sheet_name = "sheet"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(url, dtype=str).fillna("")
    # Remove any extra spaces around column names for easier access
    df.columns = df.columns.str.strip()
    return df

def generate_invoice_pdf(company_info, customer_ref, invoice_number, invoice_date, sar_rate, bank_details, items):
    """
    Render the invoice HTML template and generate a PDF using WeasyPrint.
    """
    try:
        with open("invoice_template.html", "r") as file:
            template_content = file.read()
    except FileNotFoundError:
        st.error("Error: invoice_template.html not found. Please ensure it is in the same directory as app.py.")
        return None

    template = Template(template_content)
    total_usd = sum(item['qty'] * item['rate'] for item in items)
    total_sar = sum(item['qty'] * item['rate'] * sar_rate for item in items)

    rendered_html = template.render(
        company_info=company_info,
        customer_ref=customer_ref,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        sar_rate=sar_rate,
        bank_details=bank_details,
        items=items,
        total_usd=total_usd,
        total_sar=total_sar
    )

    pdf_file_path = "invoice.pdf"
    HTML(string=rendered_html).write_pdf(pdf_file_path)
    return pdf_file_path

st.title("Invoice Generator")

st.subheader("Select Company Info from Google Sheets")
company_data = get_company_data()
if company_data is not None and "Company name" in company_data.columns and "Company Address" in company_data.columns:
    # Get a list of company names and let the user choose one.
    company_names = company_data["Company name"].tolist()
    selected_company = st.selectbox("Select a company", company_names)
    # Retrieve the corresponding address.
    company_address = company_data[company_data["Company name"] == selected_company]["Company Address"].iloc[0]
    company_info_default = f"{selected_company}\n{company_address}"
else:
    company_info_default = "Enter company info manually."

# Editable Company Info input field.
company_info = st.text_area("Company Info", company_info_default)

# Other invoice details.
customer_ref = st.text_area("Customer Reference", """AGFZE/CU/TAT/---/2025
CNTR: 1ST
CONTAINER NO: YMLU3386328""")
invoice_number = st.text_input("Invoice Number", "30250124")
invoice_date = st.date_input("Invoice Date", date.today())
sar_rate = st.number_input("Dollar to SAR Rate", value=3.7475, step=0.0001)
bank_details = st.text_area("Bank Details", """BANK DETAILS: TABIB AL ARABIA FOR ENVIRONMENTAL SERVICES CO.
RIYAD BANK.
DOLLAR ACCOUNT A/C NO:3274336190440
IBAN NO:SA4920000003274336190440
BIN KHALDOON ST. BRANCH
SWIFT CODE:RIBLSARI""")

st.subheader("Items")
items = []
num_items = st.number_input("Number of items", min_value=1, value=1, step=1)
for i in range(num_items):
    with st.expander(f"Item {i+1}"):
        desc = st.text_input(f"Description {i+1}", "Cu Birch Cliff Scrap", key=f"desc_{i}")
        qty = st.number_input(f"Quantity {i+1}", value=19.332, step=0.001, key=f"qty_{i}")
        rate = st.number_input(f"Rate (USD) {i+1}", value=8380.00, step=0.01, key=f"rate_{i}")
        items.append({"desc": desc, "qty": qty, "rate": rate})

if st.button("Generate Invoice PDF"):
    pdf_file_path = generate_invoice_pdf(
        company_info, customer_ref, invoice_number, invoice_date, sar_rate, bank_details, items
    )
    if pdf_file_path:
        with open(pdf_file_path, "rb") as f:
            st.download_button("Download Invoice", data=f.read(), file_name="invoice.pdf", mime="application/pdf")
