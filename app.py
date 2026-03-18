import streamlit as st
from PIL import Image, ImageEnhance
import pytesseract
import sqlite3
import pandas as pd
import re
import json
import smtplib
from email.mime.text import MIMEText
import fitz
import streamlit as st


# --------------------------------------------------
# UI ENHANCEMENT (ADDED - DOES NOT CHANGE YOUR CODE)
# --------------------------------------------------
st.set_page_config(
    page_title="AI Invoice OCR Inventory System",
    page_icon="📦",
    layout="wide"
)

st.markdown("""
<style>

.stApp{
background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
color:white;
}

h1,h2,h3{
color:white;
font-weight:600;
}

.stButton>button{
background:linear-gradient(90deg,#00c6ff,#0072ff);
color:white;
border-radius:10px;
height:45px;
font-size:16px;
font-weight:600;
border:none;
}

.stButton>button:hover{
background:linear-gradient(90deg,#0072ff,#00c6ff);
}

.stTextInput>div>div>input{
border-radius:10px;
background:#1c1c1c;
color:white;
}

.stTextArea textarea{
background:#1c1c1c;
color:white;
}

.stDataFrame{
background:#1c1c1c;
}

.css-1d391kg{
background:#111;
}

div[data-testid="metric-container"]{
background: rgba(255,255,255,0.05);
border-radius:15px;
padding:15px;
box-shadow:0px 4px 15px rgba(0,0,0,0.3);
}

</style>
""",unsafe_allow_html=True)
# --------------------------------------------------


pytesseract.pytesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


import streamlit as st

# -----------------------------
# ADMIN LOGIN
# -----------------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "invoice123"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# -----------------------------
# LOGIN PAGE
# -----------------------------
if not st.session_state.authenticated:

    st.title("AI Invoice OCR Inventory System")
    st.subheader("Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.success("Login Successful")
            st.rerun()

        else:
            st.error("Invalid username or password")

    st.stop()


# -----------------------------
# NORMALIZE PRODUCT NAME
# -----------------------------
def normalize_product_name(name):
    name = name.lower()
    name = re.sub(r'[^a-zA-Z ]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


# -----------------------------
# AUTO FIELD EXTRACTION
# -----------------------------
def extract_invoice_fields(text):

    invoice_number = None
    invoice_date = None
    gstin = None

    inv_match = re.search(r'(INV[- ]?\d+)', text, re.IGNORECASE)
    if inv_match:
        invoice_number = inv_match.group()

    date_match = re.search(r'\d{2}/\d{2}/\d{4}', text)
    if date_match:
        invoice_date = date_match.group()

    gst_match = re.search(r'\d{2}[A-Z]{5}\d{4}[A-Z]\dZ\d', text)
    if gst_match:
        gstin = gst_match.group()

    return invoice_number, invoice_date, gstin


# -----------------------------
# DATABASE
# -----------------------------
conn = sqlite3.connect("inventory_system.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS products(
product_id INTEGER PRIMARY KEY AUTOINCREMENT,
product_name TEXT UNIQUE,
stock INTEGER,
min_stock INTEGER,
last_price INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices(
id INTEGER PRIMARY KEY AUTOINCREMENT,
invoice_number TEXT,
supplier_name TEXT,
invoice_date TEXT,
invoice_type TEXT,
grand_total INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory_log(
product_name TEXT,
change_qty INTEGER,
transaction_type TEXT,
invoice_number TEXT,
timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()


# -----------------------------
# EMAIL ALERT
# -----------------------------
def send_low_stock_email(product, qty):

    sender = "kavianand.2401103@srec.ac.in"
    password = "jigtmemefspkdrqi"
    receiver = "kavianand.2401103@srec.ac.in"

    subject = "Inventory Low Stock Alert"

    body = f"""
Low Stock Warning

Product: {product}
Remaining Stock: {qty}

Please restock soon.
"""

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com",465) as server:
            server.login(sender,password)
            server.send_message(msg)
    except Exception as e:
        st.error("Email sending failed")


# -----------------------------
# IMAGE PREPROCESSING
# -----------------------------
def preprocess_image(img):

    gray = img.convert("L")
    enhancer = ImageEnhance.Contrast(gray)

    return enhancer.enhance(2)


# -----------------------------
# ITEM EXTRACTION
# -----------------------------
def extract_items(text):

    items=[]
    lines=text.split("\n")

    for line in lines:

        match=re.search(r"([A-Za-z ]+)\s+(\d+)\s+(\d+)\s+(\d+)",line)

        if match:

            items.append({
                "name":match.group(1).strip(),
                "qty":int(match.group(2)),
                "rate":int(match.group(3)),
                "amount":int(match.group(4))
            })

    return items


# -----------------------------
# DETECT INVOICE TYPE
# -----------------------------
def detect_invoice_type(text):

    text=text.lower()

    if "thank you for your purchase" in text:
        return "sales"

    if "purchase invoice" in text or "stock loaded" in text:
        return "purchase"

    return "unknown"


# -----------------------------
# STREAMLIT UI
# -----------------------------
st.title("AI Invoice OCR Inventory System")

uploaded_file = st.file_uploader(
    "Upload Invoice (Image or PDF)",
    type=["png","jpg","jpeg","pdf"]
)

if uploaded_file is not None:

    try:

        if uploaded_file.type == "application/pdf":

            pdf_bytes = uploaded_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = doc.load_page(0)
            pix = page.get_pixmap()
            image = Image.frombytes("RGB",[pix.width,pix.height],pix.samples)

        else:

            image = Image.open(uploaded_file)

    except Exception:
        st.error("Unable to open the uploaded file.")
        st.stop()

    st.subheader("Invoice Preview")
    st.image(image,use_column_width=True)

    if st.button("Process Invoice"):

        try:

            processed = preprocess_image(image)
            text = pytesseract.image_to_string(processed)

            if text.strip() == "":
                st.warning("OCR could not detect readable text.")
                st.stop()

            st.session_state["ocr_text"] = text
            st.session_state["items"] = extract_items(text)
            st.session_state["invoice_type"] = detect_invoice_type(text)

            inv,date,gst = extract_invoice_fields(text)

            st.session_state["invoice_number"] = inv
            st.session_state["invoice_date"] = date
            st.session_state["gstin"] = gst

        except Exception:
            st.error("OCR processing failed.")
            st.stop()


# -----------------------------
# OCR RESULTS
# -----------------------------
if "ocr_text" in st.session_state:

    st.subheader("OCR Text")
    st.text_area("Detected Text",st.session_state["ocr_text"],height=200)

    items = st.session_state["items"]

    json_data = {

        "supplier":{
            "name":"ABC Textiles",
            "gstin":st.session_state.get("gstin")
        },

        "invoice":{
            "invoice_number":st.session_state.get("invoice_number"),
            "invoice_date":st.session_state.get("invoice_date")
        },

        "invoice_type":st.session_state["invoice_type"],

        "items":items
    }

    editable_json = st.text_area(
        "Edit JSON if needed",
        json.dumps(json_data,indent=4),
        height=300
    )

    try:
        json_data=json.loads(editable_json)
    except Exception:
        st.error("Invalid JSON format")
        st.stop()

    st.json(json_data)


# -----------------------------
# MISSING FIELD DETECTION
# -----------------------------
    missing_fields = []

    if not json_data["supplier"].get("name"):
        missing_fields.append("Supplier Name")

    if not json_data["supplier"].get("gstin"):
        missing_fields.append("GSTIN")

    if not json_data["invoice"].get("invoice_number"):
        missing_fields.append("Invoice Number")

    if not json_data["invoice"].get("invoice_date"):
        missing_fields.append("Invoice Date")

    for i,item in enumerate(json_data["items"]):

        if not item.get("name"):
            missing_fields.append(f"Item {i+1} Name")

        if not item.get("qty"):
            missing_fields.append(f"Item {i+1} Quantity")

        if not item.get("rate"):
            missing_fields.append(f"Item {i+1} Rate")

    if missing_fields:

        st.warning("⚠ Missing fields detected")

        for field in missing_fields:
            st.write("•",field)

        st.info("You can correct them in the JSON editor above.")


# -----------------------------
# OCR vs JSON COMPARISON
# -----------------------------
    ocr_text = st.session_state["ocr_text"].lower()
    comparison_errors = []

    if json_data["supplier"]["name"] and json_data["supplier"]["name"].lower() not in ocr_text:
        comparison_errors.append("Supplier name differs from OCR text")

    if json_data["supplier"]["gstin"] and json_data["supplier"]["gstin"].lower() not in ocr_text:
        comparison_errors.append("GSTIN differs from OCR text")

    if json_data["invoice"]["invoice_number"] and json_data["invoice"]["invoice_number"].lower() not in ocr_text:
        comparison_errors.append("Invoice number differs from OCR text")

    if json_data["invoice"]["invoice_date"] and json_data["invoice"]["invoice_date"].lower() not in ocr_text:
        comparison_errors.append("Invoice date differs from OCR text")

    for i,item in enumerate(json_data["items"]):
        if item["name"] and item["name"].lower() not in ocr_text:
            comparison_errors.append(f"Item {i+1} name not found in OCR text")

    if comparison_errors:

        st.warning("⚠ OCR vs JSON mismatch detected")

        for err in comparison_errors:
            st.write("•",err)

        st.info("Verify the extracted data and update JSON if required.")


# -----------------------------
# EXTRACTION ACCURACY
# -----------------------------
    total_fields = 4 + (len(json_data["items"]) * 3)

    missing_count = len(missing_fields)
    comparison_count = len(comparison_errors)

    error_count = missing_count + comparison_count

    extracted_fields = total_fields - error_count

    accuracy = (extracted_fields / total_fields) * 100

    st.subheader("Extraction Accuracy")

    st.progress(int(accuracy))

    st.write(f"Extraction Accuracy: **{accuracy:.2f}%**")


    st.download_button(
        "Download JSON",
        json.dumps(json_data,indent=4),
        "invoice_data.json"
    )

    st.download_button(
        "Download CSV",
        pd.DataFrame(json_data["items"]).to_csv(index=False),
        "invoice_items.csv"
    )


# -----------------------------
# UPDATE INVENTORY
# -----------------------------
    if st.button("Update Inventory"):

        inv=json_data["invoice"]["invoice_number"]

        cursor.execute("""
        INSERT INTO invoices
        (invoice_number, supplier_name, invoice_date, invoice_type, grand_total)
        VALUES (?,?,?,?,?)
        """,
        (
            inv,
            json_data["supplier"]["name"],
            json_data["invoice"]["invoice_date"],
            json_data["invoice_type"],
            0
        ))

        for item in json_data["items"]:

            product = normalize_product_name(item["name"])

            cursor.execute(
            "SELECT stock FROM products WHERE product_name=?",
            (product,)
            )

            result=cursor.fetchone()

            if result:

                stock=result[0]

                if json_data["invoice_type"]=="purchase":
                    new_stock=stock+item["qty"]
                    change=item["qty"]

                else:
                    new_stock=stock-item["qty"]
                    change=-item["qty"]

                cursor.execute("""
                UPDATE products
                SET stock=?, last_price=?
                WHERE product_name=?
                """,(new_stock,item["rate"],product))

            else:

                new_stock=item["qty"]

                cursor.execute("""
                INSERT INTO products(product_name,stock,min_stock,last_price)
                VALUES(?,?,?,?)
                """,(product,new_stock,10,item["rate"]))

                change=item["qty"]

            cursor.execute("""
            INSERT INTO inventory_log
            (product_name,change_qty,transaction_type,invoice_number)
            VALUES(?,?,?,?)
            """,(product,change,json_data["invoice_type"],inv))

        conn.commit()

        st.success("Inventory Updated")


col1, col2 = st.columns([8,1])

with col2:
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()


# -----------------------------
# INVENTORY DASHBOARD
# -----------------------------
st.subheader("Inventory Dashboard")

inventory_df=pd.read_sql_query(
"SELECT product_name,stock,min_stock FROM products",
conn
)

st.dataframe(inventory_df)


# -----------------------------
# LOW STOCK ALERTS
# -----------------------------
st.subheader("Low Stock Alerts")

for index,row in inventory_df.iterrows():

    if row["stock"]<=row["min_stock"]:

        st.error(
        f"LOW STOCK ALERT: {row['product_name']} only {row['stock']} left"
        )

        send_low_stock_email(row["product_name"],row["stock"])


# -----------------------------
# INVENTORY GRAPH
# -----------------------------
st.subheader("Inventory Overview")

chart_df=inventory_df.set_index("product_name")

st.bar_chart(chart_df["stock"])


# -----------------------------
# SUPPLIER ANALYTICS
# -----------------------------
st.subheader("Supplier Analytics")

supplier_df=pd.read_sql_query("""
SELECT supplier_name, COUNT(*) as invoices
FROM invoices
GROUP BY supplier_name
""",conn)

st.bar_chart(supplier_df.set_index("supplier_name"))


# -----------------------------
# INVENTORY HISTORY
# -----------------------------
st.subheader("Inventory Movement History")

history_df=pd.read_sql_query(
"SELECT * FROM inventory_log",
conn
)
st.dataframe(history_df)