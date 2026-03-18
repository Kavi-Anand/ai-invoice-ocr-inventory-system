# 📦 AI Invoice OCR Inventory System

## 🚀 Overview

The **AI Invoice OCR Inventory System** is a smart application that automates invoice processing and inventory management. It extracts data from invoices using OCR and converts it into structured information to update stock levels, track inventory, and generate analytics.

---

## ✨ Features

* 🔐 Admin Login Authentication
* 📄 Invoice Upload (Image & PDF)
* 🔍 OCR Text Extraction using Tesseract
* 🧠 Smart Data Extraction (Invoice + Items)
* 📝 Editable JSON Output
* ⚠ Missing Field Detection
* 🔎 OCR vs JSON Validation
* 📊 Extraction Accuracy Score
* 📦 Automatic Inventory Update
* 📉 Low Stock Alerts (Email Notification)
* 📊 Inventory Dashboard & Charts
* 🏢 Supplier Analytics
* 🧾 Inventory Movement History

---

## 🛠 Tech Stack

* **Frontend:** Streamlit
* **Backend:** Python
* **OCR Engine:** Tesseract OCR
* **Database:** SQLite
* **Libraries:** PIL, pandas, pytesseract, fitz (PyMuPDF)

---

## ⚙️ How It Works

1. Upload invoice (image or PDF)
2. Image is preprocessed (grayscale + contrast)
3. OCR extracts raw text
4. System identifies:

   * Invoice details
   * Supplier info
   * Item list
5. Data is converted into structured JSON
6. User can edit/validate extracted data
7. Inventory updates automatically
8. Dashboard reflects stock changes

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

## ▶️ Installation & Run

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

### 4. Install Tesseract OCR

Download from: https://github.com/tesseract-ocr/tesseract

Update path in code if needed:

```python
pytesseract.pytesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### 5. Run the application

```bash
streamlit run app.py
```

---

## 📊 Output Features

* JSON export of invoice data
* CSV export of items
* Real-time inventory dashboard
* Low stock email alerts

---

## 🔒 Security Note

Sensitive information such as email credentials should be stored using environment variables instead of hardcoding.

---

## 🎯 Use Cases

* Small businesses
* Retail inventory management
* Automated invoice processing
* Stock tracking systems

---

## 👨‍💻 Author

**Kavi Anand**

---

## ⭐ Future Improvements

* AI-based invoice parsing (LLM integration)
* Multi-user authentication
* Cloud deployment
* Advanced analytics dashboard
