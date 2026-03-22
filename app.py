import streamlit as st
from PIL import Image, ImageEnhance
import pytesseract
import sqlite3
import pandas as pd
import re
import json
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai

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

    # Use columns to make the login box smaller and centered
    _, col, _ = st.columns([1, 1, 1])
    
    with col:
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
    # Do not strip numbers or symbols so AI extraction accuracy is preserved!
    name = str(name).strip()
    name = re.sub(r'\s+', ' ', name)
    return name.title()


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

# Safe Alter Table queries for new columns
def add_column_if_not_exists(table, column, metadata):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {metadata}")
        conn.commit()
    except sqlite3.OperationalError:
        pass

add_column_if_not_exists("products", "market_price", "INTEGER DEFAULT 0")
add_column_if_not_exists("invoices", "gst", "INTEGER DEFAULT 0")
add_column_if_not_exists("invoices", "total_with_gst", "INTEGER DEFAULT 0")

conn.commit()


# -----------------------------
# EMAIL ALERT
# -----------------------------
def send_low_stock_email(product, qty, sender, password, receiver):

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
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        st.success(f"Low stock email sent for {product}")
    except smtplib.SMTPAuthenticationError:
        st.error(f"Failed to email alert for '{product}': Your Google App Password was rejected (Auth Error 535). Please update it in the '📧 Email Settings' sidebar.")
    except Exception as e:
        st.error(f"Email sending failed.\nError: {e}")


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
    
    if any(word in text for word in ["thank you", "come again", "sold", "sales"]):
        return "sales"
        
    if any(word in text for word in ["loaded", "uploaded", "purchase invoice", "stock loaded", "bought", "received"]):
        return "purchase"
        
    return "unknown"




# -----------------------------
# GEMINI AI RAW TEXT EXTRACTION
# -----------------------------
def gemini_get_raw_text(image_obj, api_key, model_name="gemini-1.5-flash"):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        prompt = "Extract all text from this image exactly as it appears. Include all keywords, amounts, and descriptions. Return only the extracted text."
        response = model.generate_content([prompt, image_obj])
        return response.text.strip()
    except Exception as e:
        return None

# -----------------------------
# GEMINI AI EXTRACTION (MULTIMODAL)
# -----------------------------
def gemini_extract(image_obj, text, api_key, model_name="gemini-1.5-flash"):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    prompt = f"""
You are an expert OCR parser. Extract both printed and handwritten text from the provided invoice image.
As an additional reference, here is the raw machine OCR text previously extracted (which may have errors):
'''
{text}
'''
Convert the extracted data into a JSON object strictly following this structure. 
Return ONLY valid JSON.
""" + """
{
    "supplier": {
        "name": "string or null",
        "gstin": "string or null"
    },
    "invoice": {
        "invoice_number": "string or null",
        "invoice_date": "string or null"
    },
    "invoice_type": "purchase or sales or unknown",
    "items": [
        {
            "name": "string",
            "qty": integer,
            "rate": integer,
            "amount": integer
        }
    ]
}
"""
    try:
        response = model.generate_content([prompt, image_obj])
        res_text = response.text.strip()
        if res_text.startswith("```json"):
            res_text = res_text[7:]
        if res_text.startswith("```"):
            res_text = res_text[3:]
        if res_text.endswith("```"):
            res_text = res_text[:-3]
        return json.loads(res_text.strip())
    except Exception as e:
        st.error(f"AI Extraction Exception: {e}")
        return None


# -----------------------------
# SIDEBAR UI NAVIGATION
# -----------------------------
with st.sidebar:
    st.header("⚙️ Dashboard Navigation")
    menu = st.radio("Menu", [
        "Dashboard", 
        "Scan Invoice", 
        "Process Invoice", 
        "Inventory", 
        "Market Rate", 
        "GST Calculator", 
        "Analytics", 
        "History", 
        "Logout"
    ])
    st.divider()
    st.subheader("🔑 API Settings")
    gemini_api_key = st.text_input("Gemini API Key", type="password", help="Needed for AI JSON Extraction")
    
    if gemini_api_key:
        try:
            genai.configure(api_key=gemini_api_key)
            models = [m.name.split("/")[-1] for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
            def_idx = models.index("gemini-pro-vision") if "gemini-pro-vision" in models else 0
            ai_model_selection = st.selectbox("Gemini Model", models, index=def_idx, help="Dynamically fetched available models based on your API key format.")
        except Exception:
            ai_model_selection = st.selectbox("Gemini Model", ["gemini-pro-vision", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.5-flash-latest"], help="Select model carefully. Try pro-vision if older SDK.")
    else:
        ai_model_selection = st.selectbox("Gemini Model", ["gemini-pro-vision", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.5-flash-latest"])

    st.divider()
    st.subheader("📧 Email Settings")
    sender_email = st.text_input("Sender Email", value="kavianand.2401103@srec.ac.in")
    email_app_password = st.text_input("App Password", value="ivejxkqnairuxdxp", type="password", help="Update if you face 535 BadCredentials error.")
    receiver_email = st.text_input("Receiver Email", value="kavianand.2401103@srec.ac.in")


# -----------------------------
# PAGES ROUTING
# -----------------------------
if menu == "Dashboard":
    # -----------------------------
    # INVENTORY DASHBOARD
    # -----------------------------
    st.subheader("Inventory Dashboard")

    inventory_df=pd.read_sql_query(
    "SELECT product_id, product_name, stock, min_stock, last_price, market_price FROM products",
    conn
    )
    
    # KPIs / Floating Boards
    
    custom_cards_css = """
    <style>
    .kpi-board {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius:15px;
        padding:20px;
        box-shadow:0px 4px 15px rgba(0,0,0,0.3);
        text-align: center;
        transition: all 0.3s ease;
        height: 130px;
        color: white;
        position: relative;
        overflow: hidden;
        cursor: pointer;
    }
    .kpi-board .details {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(135deg,rgba(0,198,255,0.9),rgba(0,114,255,0.9));
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: all 0.4s ease;
        padding: 15px;
        font-size: 15px;
        font-weight: 600;
        border-radius: 15px;
    }
    .kpi-board:hover .details {
        opacity: 1;
    }
    .kpi-board h2 {
        margin: 0;
        font-size: 34px;
        color: #00c6ff;
    }
    .kpi-board p {
        margin: 5px 0 0 0;
        font-size: 16px;
        font-weight: 500;
        color: #eee;
    }
    </style>
    """
    st.markdown(custom_cards_css, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    total_products = len(inventory_df)
    low_stock = len(inventory_df[inventory_df['stock'] <= inventory_df['min_stock']])
    
    cursor.execute("SELECT SUM(stock * market_price) FROM products")
    val_res = cursor.fetchone()
    total_value = val_res[0] if val_res and val_res[0] else 0
    total_invoices = pd.read_sql_query("SELECT COUNT(*) FROM invoices", conn).iloc[0,0]
    
    with col1:
        st.markdown(f'<div class="kpi-board"><h2>{total_products}</h2><p>📦 Total Products</p><div class="details">The total count of unique products tracked in your inventory.</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-board"><h2>{low_stock}</h2><p>⚠️ Low Stock Items</p><div class="details">Products whose current stock is equal to or below their safe minimum level.</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="kpi-board"><h2>₹{total_value:,.2f}</h2><p>💰 Market Value</p><div class="details">Calculated as (Stock × Market Price) for all registered products.</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="kpi-board"><h2>{total_invoices}</h2><p>📄 Total Invoices</p><div class="details">The aggregate total of all historically processed invoices.</div></div>', unsafe_allow_html=True)

    
    st.divider()
    
    st.subheader("Database Cleanup (Edit & Save Full Inventory)")
    st.info("You can now safely rename products, fix negative stocks, edit market prices, and delete messy rows!")
    edited_df = st.data_editor(
        inventory_df, 
        key="full_inventory_editor",
        use_container_width=True,
        num_rows="dynamic"
    )
    
    if st.button("💾 Save Database Changes"):
        cursor.execute("DELETE FROM products")
        for idx, row in edited_df.fillna(0).iterrows():
            if not str(row['product_name']).strip() == "0":
                cursor.execute("""
                INSERT INTO products (product_id, product_name, stock, min_stock, last_price, market_price) 
                VALUES (?, ?, ?, ?, ?, ?)
                """, (row['product_id'], row['product_name'], int(row['stock']), int(row['min_stock']), row['last_price'], row['market_price']))
        conn.commit()
        st.success("✅ Database Cleaned and Neatly Updated!")
        st.rerun()


    # -----------------------------
    # LOW STOCK ALERTS
    # -----------------------------
    st.subheader("Low Stock Alerts")

    for index,row in inventory_df.iterrows():
        if row["stock"]<=row["min_stock"]:
            st.error(
            f"LOW STOCK ALERT: {row['product_name']} only {row['stock']} left"
            )
            if sender_email and email_app_password and receiver_email:
                send_low_stock_email(row["product_name"], row["stock"], sender_email, email_app_password, receiver_email)
            else:
                st.warning("Please configure Sender Email and App Password in the sidebar to send low-stock alerts.")

    # -----------------------------
    # INVENTORY GRAPH
    # -----------------------------
    st.subheader("Inventory Overview")

    chart_df=inventory_df.set_index("product_name")
    st.bar_chart(chart_df["stock"])


elif menu == "Scan Invoice":
    st.title("📷 Scan Invoice using Camera")
    
    image_cam = st.camera_input("Capture Invoice Image from Device Camera")
    
    if image_cam is not None:
        pil_img = Image.open(image_cam)
        st.image(pil_img, caption="Captured Setup", use_column_width=True)
        
        if st.button("Process Captured Invoice"):
            try:
                processed = preprocess_image(pil_img)
                if gemini_api_key:
                    with st.spinner(f"Extracting raw OCR text using {ai_model_selection}..."):
                        text = gemini_get_raw_text(pil_img, gemini_api_key, ai_model_selection)
                        if not text:
                            st.warning("AI Raw Text Extraction failed. Falling back to Tesseract.")
                            text = pytesseract.image_to_string(processed)
                else:
                    text = pytesseract.image_to_string(processed)

                if text.strip() == "":
                    st.warning("OCR could not detect readable text.")
                else:
                    st.session_state["raw_image"] = pil_img
                    st.session_state["ocr_text"] = text
                    st.session_state["items"] = extract_items(text)
                    st.session_state["invoice_type"] = detect_invoice_type(text)

                    inv,date,gst = extract_invoice_fields(text)

                    st.session_state["invoice_number"] = inv
                    st.session_state["invoice_date"] = date
                    st.session_state["gstin"] = gst
                    
                    st.success("Camera Scan complete! The text has been stored in state. Please navigate to 'Process Invoice' to review and save.")
            except Exception as e:
                st.error(f"OCR processing failed: {e}")


elif menu == "Process Invoice":
    # -----------------------------
    # STREAMLIT UI
    # -----------------------------
    st.title("📄 Process Invoice Document")

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

        if st.button("Run OCR Pipeline"):
            try:
                processed = preprocess_image(image)
                
                if gemini_api_key:
                    with st.spinner(f"Extracting raw OCR text using {ai_model_selection}..."):
                        text = gemini_get_raw_text(image, gemini_api_key, ai_model_selection)
                        if not text:
                            st.warning("AI Raw Text Extraction failed. Falling back to Tesseract.")
                            text = pytesseract.image_to_string(processed)
                else:
                    text = pytesseract.image_to_string(processed)

                if text.strip() == "":
                    st.warning("OCR could not detect readable text.")
                    st.stop()

                st.session_state["raw_image"] = image
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
    # OCR RESULTS & AI TOGGLE
    # -----------------------------
    if "ocr_text" in st.session_state:
        st.divider()
        st.subheader("Step 2: Review Extraction & JSON Data")
        
        with st.expander("View Raw OCR Text", expanded=True):
            st.text_area("Detected Text (Provides Keywords for Logic)", st.session_state["ocr_text"], height=200)

        use_ai = st.checkbox("🤖 Use AI Extraction (Gemini API for Extractive accuracy incl. Handwriting)", value=("ai_json_data" in st.session_state))
        
        if use_ai:
            if not gemini_api_key:
                st.error("Please provide Gemini API Key in the sidebar to use AI extraction.")
            else:
                if "ai_json_data" not in st.session_state or st.button("Regenerate AI Extraction"):
                    with st.spinner(f"Analyzing structure & handwriting using {ai_model_selection}..."):
                        if "raw_image" in st.session_state and "ocr_text" in st.session_state:
                            ai_result = gemini_extract(st.session_state["raw_image"], st.session_state["ocr_text"], gemini_api_key, model_name=ai_model_selection)
                            if ai_result:
                                st.session_state["ai_json_data"] = ai_result
                                st.success("AI Extraction Complete.")
                            else:
                                st.error("AI returned malformed data. Falling back to regex.")
                                use_ai = False
                        else:
                            st.warning("No image found in session to send to AI.")
                            use_ai = False

        if use_ai and "ai_json_data" in st.session_state:
            json_data = st.session_state["ai_json_data"]
        else:
            json_data = {
                "supplier":{
                    "name":"ABC Textiles",
                    "gstin":st.session_state.get("gstin")
                },
                "invoice":{
                    "invoice_number":st.session_state.get("invoice_number"),
                    "invoice_date":st.session_state.get("invoice_date")
                },
                "invoice_type":st.session_state.get("invoice_type"),
                "items":st.session_state.get("items", [])
            }

        editable_json = st.text_area(
            "Review Auto-Mapped JSON Output",
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

        if not json_data.get("supplier",{}).get("name"): missing_fields.append("Supplier Name")
        if not json_data.get("supplier",{}).get("gstin"): missing_fields.append("GSTIN")
        if not json_data.get("invoice",{}).get("invoice_number"): missing_fields.append("Invoice Number")
        if not json_data.get("invoice",{}).get("invoice_date"): missing_fields.append("Invoice Date")

        for i,item in enumerate(json_data.get("items", [])):
            if not item.get("name"): missing_fields.append(f"Item {i+1} Name")
            if not item.get("qty"): missing_fields.append(f"Item {i+1} Quantity")
            if not item.get("rate"): missing_fields.append(f"Item {i+1} Rate")

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
        
        sup_name = json_data.get("supplier",{}).get("name")
        sup_gst = json_data.get("supplier",{}).get("gstin")
        inv_num = json_data.get("invoice",{}).get("invoice_number")
        inv_dat = json_data.get("invoice",{}).get("invoice_date")

        if sup_name and str(sup_name).lower() not in ocr_text: comparison_errors.append("Supplier name differs from OCR text")
        if sup_gst and str(sup_gst).lower() not in ocr_text: comparison_errors.append("GSTIN differs from OCR text")
        if inv_num and str(inv_num).lower() not in ocr_text: comparison_errors.append("Invoice number differs from OCR text")
        if inv_dat and str(inv_dat).lower() not in ocr_text: comparison_errors.append("Invoice date differs from OCR text")

        for i,item in enumerate(json_data.get("items",[])):
            if item.get("name") and str(item["name"]).lower() not in ocr_text:
                comparison_errors.append(f"Item {i+1} name not found in OCR text")

        if comparison_errors:
            st.warning("⚠ OCR vs JSON mismatch detected")
            for err in comparison_errors:
                st.write("•",err)
            st.info("Verify the extracted data and update JSON if required.")


    # -----------------------------
    # EXTRACTION ACCURACY
    # -----------------------------
        total_fields = 4 + (len(json_data.get("items",[])) * 3)

        missing_count = len(missing_fields)
        comparison_count = len(comparison_errors)
        error_count = missing_count + comparison_count
        
        extracted_fields = max(0, total_fields - error_count)
        if total_fields > 0:
            accuracy = (extracted_fields / total_fields) * 100
        else:
            accuracy = 0.0

        st.subheader("Extraction Accuracy")
        st.progress(int(accuracy))
        st.write(f"Extraction Accuracy: **{accuracy:.2f}%**")

        c1, c2 = st.columns(2)
        c1.download_button(
            "Download JSON",
            json.dumps(json_data,indent=4),
            "invoice_data.json"
        )
        c2.download_button(
            "Download CSV",
            pd.DataFrame(json_data.get("items",[])).to_csv(index=False),
            "invoice_items.csv"
        )
        st.divider()

    # -----------------------------
    # GST AND MARKET SUGGESTION
    # -----------------------------
        st.subheader("Step 3: Market Rate & GST Confirmation")
        
        overall_gst = st.number_input("Enter Overall GST Percentage (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
        
        final_items = []
        total_amt = 0.0
        total_gst = 0.0
        
        st.write("#### Market Suggestion System")
        with st.container():
            for idx, item in enumerate(json_data.get("items",[])):
                product = normalize_product_name(item.get("name",""))
                qty = item.get("qty", 0)
                extracted_rate = item.get("rate", 0)
                
                # Check known market attributes securely
                cursor.execute("SELECT last_price, market_price FROM products WHERE product_name=?", (product,))
                res = cursor.fetchone()
                db_last_price = res[0] if res else "No previous entries"
                db_market_price = res[1] if res else 0
                
                st.markdown(f"**Item:** {product.title()} | **Extracted Rate:** ₹{extracted_rate} | **Qty:** {qty}")
                st.write(f"- 🕒 Previous DB Price: ₹{db_last_price}")
                
                s_c1, s_c2 = st.columns([1,1])
                confirmed_rate = s_c1.number_input(f"Confirm Market Rate for {product.title()} (₹)", value=float(extracted_rate), key=f"rate_{idx}")
                
                # Math
                amt = confirmed_rate * qty
                gst_val = amt * (overall_gst / 100)
                
                s_c2.write(f"Item Amount = ₹{amt:.2f}")
                s_c2.write(f"Item GST ({overall_gst}%) = ₹{gst_val:.2f}")
                
                final_items.append({
                    "name": product,
                    "qty": qty,
                    "rate": confirmed_rate,
                    "amount": amt,
                    "gst": gst_val
                })
                total_amt += amt
                total_gst += gst_val
                st.markdown("---")
        
        grand_total = total_amt + total_gst

    # -----------------------------
    # CONFIRMATION BEFORE UPDATE
    # -----------------------------
        st.subheader("Step 4: Update Inventory")
        st.write("**Invoice Final Summary**")
        st.write(f"• Raw Amount: ₹{total_amt:.2f}")
        st.write(f"• Total GST:  ₹{total_gst:.2f}")
        st.write(f"• Grand Total: ₹{grand_total:.2f}")
        
        st.warning("Please confirm the data summary before committing changes.")
        confirm_update = st.checkbox("Confirm Inventory Update?", value=False)
        
        if st.button("💾 Save & Update Inventory", disabled=not confirm_update):

            inv = json_data.get("invoice",{}).get("invoice_number", "UNKNOWN")

            cursor.execute("""
            INSERT INTO invoices
            (invoice_number, supplier_name, invoice_date, invoice_type, grand_total, gst, total_with_gst)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                inv,
                json_data.get("supplier",{}).get("name"),
                json_data.get("invoice",{}).get("invoice_date"),
                json_data.get("invoice_type"),
                total_amt,
                total_gst,
                grand_total
            ))

            for item in final_items:

                product = item["name"]

                cursor.execute(
                "SELECT stock FROM products WHERE product_name=?",
                (product,)
                )

                result=cursor.fetchone()

                if result:
                    stock=result[0]

                    if json_data.get("invoice_type")=="purchase":
                        new_stock=stock+item["qty"]
                        change=item["qty"]
                    else:
                        new_stock=stock-item["qty"]
                        change=-item["qty"]

                    cursor.execute("""
                    UPDATE products
                    SET stock=?, last_price=?, market_price=?
                    WHERE product_name=?
                    """,(new_stock,item["rate"],item["rate"],product))

                else:
                    new_stock=item["qty"]
                    change=item["qty"]

                    cursor.execute("""
                    INSERT INTO products(product_name,stock,min_stock,last_price,market_price)
                    VALUES(?,?,?,?,?)
                    """,(product,new_stock,10,item["rate"],item["rate"]))

                cursor.execute("""
                INSERT INTO inventory_log
                (product_name,change_qty,transaction_type,invoice_number)
                VALUES(?,?,?,?)
                """,(product,change,json_data.get("invoice_type"),inv))

            conn.commit()

            st.success("✅ Inventory Updated Successfully")
            
            # Highlight the changed thing
            st.write("### Review Changes Applied:")
            changed_names = []
            for item in final_items:
                product_name = item['name']
                changed_names.append(product_name)
                change_qty = item['qty'] if json_data.get("invoice_type") == "purchase" else -item['qty']
                color = "green" if change_qty > 0 else "red"
                st.markdown(f"- **{product_name}**: Stock adjusted by <span style='color:{color}'>**{change_qty}**</span> (Confirmed Rate: ₹{item['rate']})", unsafe_allow_html=True)
                
            st.balloons()
            st.write("### Highlighted Inventory Table")
            updated_df = pd.read_sql_query("SELECT product_name, stock, min_stock, last_price, market_price FROM products", conn)
            
            # Apply row styling using Pandas functionality
            def highlight_updated_rows(row):
                if row['product_name'] in changed_names:
                    return ['background-color: rgba(0, 150, 0, 0.4)'] * len(row)
                return [''] * len(row)
                
            st.dataframe(updated_df.style.apply(highlight_updated_rows, axis=1), use_container_width=True)


elif menu == "Inventory":
    st.subheader("📦 Inventory Records")
    inv_df = pd.read_sql_query("SELECT * FROM products", conn)
    
    def highlight_risk(row):
        if row['stock'] <= row['min_stock']:
            return ['background-color: rgba(255, 0, 0, 0.3)'] * len(row)
        return [''] * len(row)
        
    st.dataframe(inv_df.style.apply(highlight_risk, axis=1), use_container_width=True, hide_index=True)


elif menu == "Market Rate":
    st.subheader("📊 Market Rate Tracking")
    st.info("Here you can observe the last purchased prices alongside the registered historical market prices.")
    market_df = pd.read_sql_query("SELECT product_name, last_price, market_price FROM products", conn)
    st.dataframe(market_df, use_container_width=True, hide_index=True)


elif menu == "GST Calculator":
    st.subheader("🧮 Standalone GST Breakdown Calculator")
    
    col_a, col_b = st.columns(2)
    with col_a:
        base_amt = st.number_input("Base Amount (₹)", min_value=0.0, value=0.0, step=100.0)
    with col_b:
        gst_percent = st.number_input("GST Rate (%)", min_value=0.0, value=0.0, step=1.0)
        
    if st.button("Compute GST Split"):
        total_gst = base_amt * (gst_percent / 100)
        cgst = total_gst / 2
        sgst = total_gst / 2
        grand = base_amt + total_gst
        
        st.success(f"### Sub-Total: **₹{base_amt:.2f}** | Grand Total (+GST) : **₹{grand:.2f}**")
        st.write("---")
        c1, c2, c3 = st.columns(3)
        c1.metric(label="IGST (Total)", value=f"₹{total_gst:.2f}")
        c2.metric(label="CGST", value=f"₹{cgst:.2f}")
        c3.metric(label="SGST", value=f"₹{sgst:.2f}")


elif menu == "Analytics":
    # -----------------------------
    # SUPPLIER ANALYTICS
    # -----------------------------
    st.subheader("📈 Supplier Analytics")

    supplier_df=pd.read_sql_query("""
    SELECT supplier_name, COUNT(*) as invoices
    FROM invoices
    GROUP BY supplier_name
    """,conn)

    st.bar_chart(supplier_df.set_index("supplier_name"))


elif menu == "History":
    # -----------------------------
    # INVENTORY HISTORY
    # -----------------------------
    st.subheader("🕑 Inventory Movement History")

    history_df=pd.read_sql_query(
    "SELECT * FROM inventory_log",
    conn
    )
    st.dataframe(history_df, use_container_width=True, hide_index=True)


elif menu == "Logout":
    st.session_state.authenticated = False
    st.rerun()