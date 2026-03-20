# 📦 AI Invoice OCR Inventory System

## 🚀 Overview

The **AI Invoice OCR Inventory System** is an advanced intelligent application that automates invoice processing and inventory management. It captures invoices through camera or file upload, extracts data using OCR, enhances it using AI, and converts it into structured information for inventory tracking and analytics.

This system reduces manual effort, improves accuracy, and provides real-time insights for business operations.

---

## ✨ Features

* 🔐 Admin Login Authentication
* 📷 Camera Scan for Invoice Capture
* 📄 Invoice Upload (Image & PDF)
* 🔍 OCR Text Extraction using Tesseract
* 🧠 AI-Based Data Extraction (Google Gemini API)
* 📝 Editable JSON Output for User Verification
* ⚠ Missing Field Detection
* 🔎 OCR vs JSON Validation
* 📊 Extraction Accuracy Score
* 💰 Market Price Suggestion System (based on previous records)
* 🧾 GST Calculation (CGST / SGST / IGST)
* 📦 Automatic Inventory Update
* 📉 Low Stock Alerts (Email Notification)
* 📊 Inventory Dashboard & Visualization
* 🏢 Supplier Analytics
* 🧾 Inventory Movement History

---

## 🛠 Tech Stack

* **Frontend:** Streamlit
* **Backend:** Python
* **OCR Engine:** Tesseract OCR
* **AI Integration:** Google Gemini API
* **Database:** SQLite
* **Libraries:** PIL, pandas, pytesseract, PyMuPDF (fitz), smtplib

---

## ⚙️ How It Works

1. Capture invoice using device camera or upload image/PDF
2. Image preprocessing is applied (grayscale + contrast enhancement)
3. OCR extracts raw text from the invoice
4. AI processes OCR text and converts it into structured JSON
5. System identifies:

   * Supplier details
   * Invoice number & date
   * Item details (name, quantity, rate, amount)
6. Market price suggestions are displayed using previous data
7. GST is calculated automatically
8. User verifies and edits extracted data if needed
9. System validates data (missing fields & mismatch detection)
10. Inventory is updated automatically
11. Dashboard updates stock levels and analytics

---

## 🧩 Project Structure

```bash
AI_INVOICE_SYSTEM/
│
├── app.py
├── login.py
├── models/
├── utils/
├── database/
├── uploads/
├── requirements.txt
└── README.md
```

---

## ▶️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/Kavi-Anand/ai-invoice-ocr-inventory-system.git
cd ai-invoice-ocr-inventory-system
```

### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔧 Configure OCR (Tesseract)

Download Tesseract OCR:
https://github.com/tesseract-ocr/tesseract

Update path in code if needed:

```python
pytesseract.pytesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

---

## 🔑 Configure AI (Gemini API)

1. Go to: https://aistudio.google.com/
2. Generate API Key
3. Add it securely using environment variables

Example:

```bash
set GEMINI_API_KEY=your_api_key_here
```

---

## ▶️ Run the Application

```bash
streamlit run app.py
```

---

## 📊 Output Features

* JSON export of invoice data
* CSV export of item list
* Real-time inventory dashboard
* Low stock email alerts
* Supplier analytics visualization

---

## 🔒 Security Note

Sensitive data such as API keys and email credentials should not be hardcoded. Use environment variables for secure configuration.

---

## 🎯 Use Cases

* Small and medium businesses
* Retail inventory management
* Automated invoice processing
* Warehouse stock tracking
* Accounting and ERP integration

---

## 🚀 Key Highlights

* Combines OCR + AI for high accuracy extraction
* Supports real-time camera-based invoice scanning
* Intelligent inventory automation with alerts
* Scalable and easy-to-use dashboard system

---

## 👨‍💻 Author

**Kavi Anand**

---

## ⭐ Future Improvements

* Advanced AI table detection for complex invoices
* Multi-user authentication system
* Cloud deployment (Streamlit Cloud / AWS)
* Real-time market price API integration
* Mobile application support
