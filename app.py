import streamlit as st
import pandas as pd
from datetime import date
from jinja2 import Template
from weasyprint import HTML
from num2words import num2words

# Invoice Template as a Multi-line String
invoice_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Invoice</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      margin: 40px;
      background-color: #f9f9f9;
      color: #333;
    }
    .invoice-header {
      text-align: center;
      font-size: 32px;
      font-weight: bold;
      margin-bottom: 20px;
      color: #2a7ae2;
    }
    .invoice-details {
      margin-bottom: 20px;
      padding: 10px;
      background-color: #fff;
      border: 1px solid #ddd;
      border-radius: 5px;
    }
    .invoice-details p {
      margin: 5px 0;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background-color: #fff;
      margin-bottom: 20px;
    }
    th, td {
      border: 1px solid #ccc;
      padding: 10px;
      text-align: center;
    }
    th {
      background-color: #2a7ae2;
      color: #fff;
    }
    .total {
      font-weight: bold;
      background-color: #f0f0f0;
    }
    .amount-words {
      font-style: italic;
      margin-top: 10px;
    }
    .bank-details {
      margin-top: 20px;
      padding: 10px;
      background-color: #e6f2ff;
      border: 1px solid #b3d1ff;
      border-radius: 5px;
    }
  </style>
</head>
<body>
  <!-- Invoice Number as the Main Heading -->
  <div class="invoice-header">{{ invoice_number }}</div>

  <div class="invoice-details">
    <p><strong>Company:</strong> {{ company_info }}</p>
    <p><strong>Customer Ref:</strong> {{ customer_ref }}</p>
    <p><strong>Date:</strong> {{ invoice_date }}</p>
    <p><strong>SAR Rate:</strong> {{ sar_rate }}</p>
  </div>

  <table>
    <tr>
      <th>Description</th>
      <th>Quantity</th>
      <th>Rate (USD)</th>
      <th>Total (USD)</th>
      <th>Total (SAR)</th>
    </tr>
    {% for item in items %}
    <tr>
      <td>{{ item.desc }}</td>
      <td>{{ item.qty }}</td>
      <td>{{ "%.2f"|format(item.rate) }}</td>
      <td>{{ "%.2f"|format(item.qty * item.rate) }}</td>
      <td>{{ "%.2f"|format(item.qty * item.rate * sar_rate) }}</td>
    </tr>
    {% endfor %}
    <tr class="total">
      <td colspan="3">Grand Total</td>
      <td>{{ "%.2f"|format(total_usd) }}</td>
      <td>{{ "%.2f"|format(total_sar) }}</td>
    </tr>
  </table>

  <div class="amount-words">
    <p><strong>Total Amount (in words):</strong> {{ total_usd_words }}</p>
  </div>

  <div class="bank-details">
    <p><strong>Bank Details:</strong><br>{{ bank_details }}</p>
  </div>
</body>
</html>
"""

def get_company_data():
    """
    Fetch company data from a public Google Sheet using the CSV export URL.
    The Google Sheet should have two columns: "Company Name" and "Company Address".
    """
    sheet_id = "1tj__5HXGHKOgJBwtW8VhE0jeW4Us7h_OeO7rtNN4d64"  # Your sheet ID
    sheet_name = "Sheet1"  # Adjust if needed
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(url, dtype=str).fillna("")
        df.columns = df.columns.str.strip()  # Clean column names
        return df
    except Exception as e:
        st.error(f"Error fetching company data: {e}")
        return None

def generate_invoice_pdf(company_info, customer_ref, invoice_number, invoice_date, sar_rate, bank_details, items):
    """
    Render the invoice HTML template and generate a PDF using WeasyPrint.
    Also converts the USD total into words.
    """
    total_usd = sum(item['qty'] * item['rate'] for item in items)
    total_sar = sum(item['qty'] * item['rate'] * sar_rate for item in items)
    # Convert total USD amount to words (e.g., "One Hundred Twenty-Three Dollars and 45/100")
    total_usd_words = num2words(total_usd, to='currency', lang='en')
    
    template = Template(invoice_template)
    rendered_html = template.render(
        company_info=company_info,
        customer_ref=customer_ref,
        invoice_number=invoice_number,
        invoice_date=invoice_date.strftime("%Y-%m-%d"),
        sar_rate=sar_rate,
        bank_details=bank_details,
        items=items,
        total_usd=total_usd,
        total_sar=total_sar,
        total_usd_words=total_usd_words
    )

    pdf_file_path = "invoice.pdf"
    HTML(string=rendered_html).write_pdf(pdf_file_path)
    return pdf_file_path

# --- Streamlit Application ---

st.title("Invoice Generator")

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
                company_address = company_data.loc[
                    company_data["Company Name"] == selected_company, "Company Address"
                ].iloc[0]
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

company_info = st.text_area("Company Info", value=company_info_default, key="company_info_text")

# --- Other Invoice Inputs ---
customer_ref = st.text_area("Customer Reference", "AGFZE/CU/TAT/---/2025\nCNTR: 1ST\nCONTAINER NO: YMLU3386328")
invoice_number = st.text_input("Invoice Number", "30250124")
invoice_date = st.date_input("Invoice Date", date.today())
sar_rate = st.number_input("Dollar to SAR Rate", value=3.7475, step=0.0001)
bank_details = st.text_area("Bank Details", 
"""BANK DETAILS: TABIB AL ARABIA FOR ENVIRONMENTAL SERVICES CO.
RIYAD BANK.
DOLLAR ACCOUNT A/C NO:3274336190440
IBAN NO:SA4920000003274336190440
BIN KHALDOON ST. BRANCH
SWIFT CODE:RIBLSARI""")

# --- Invoice Items Section ---
st.subheader("Items")
items = []
num_items = st.number_input("Number of items", min_value=1, value=1, step=1, key="num_items")

for i in range(num_items):
    with st.expander(f"Item {i+1}"):
        desc = st.text_input(f"Description {i+1}", "Cu Birch Cliff Scrap", key=f"desc_{i}")
        qty = st.number_input(f"Quantity {i+1}", value=19.332, step=0.001, key=f"qty_{i}")
        base_rate = st.number_input(f"Rate (USD) {i+1}", value=8380.00, step=0.01, key=f"rate_{i}")
        
        # LME Toggle and Fractional Input
        lme_toggle = st.checkbox("Enable LME for this item?", key=f"lme_toggle_{i}")
        lme_multiplier = 1.0
        if lme_toggle:
            lme_percentage = st.slider(
                "LME Percentage (40.00% - 100.00%)",
                min_value=40.00, 
                max_value=100.00, 
                value=100.00, 
                step=0.01,
                format="%.2f",
                key=f"lme_percentage_{i}"
            )
            lme_multiplier = lme_percentage / 100.0
        
        final_rate = base_rate * lme_multiplier
        items.append({
            "desc": desc,
            "qty": qty,
            "rate": final_rate
        })

# --- Generate and Download PDF ---
if st.button("Generate Invoice PDF"):
    pdf_file_path = generate_invoice_pdf(
        company_info, 
        customer_ref, 
        invoice_number, 
        invoice_date, 
        sar_rate, 
        bank_details, 
        items
    )
    if pdf_file_path:
        with open(pdf_file_path, "rb") as f:
            st.download_button("Download Invoice", data=f.read(), file_name="invoice.pdf", mime="application/pdf")
