import streamlit as st

# -----------------------------
# ADMIN CREDENTIALS
# -----------------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "invoice123"


# -----------------------------
# SESSION STATE
# -----------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


# -----------------------------
# LOGIN PAGE
# -----------------------------
st.set_page_config(page_title="Login", layout="centered")

st.title("AI Invoice OCR Inventory System")
st.subheader("Admin Login")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:

        st.session_state.authenticated = True
        st.success("Login successful")

        st.switch_page("app")   # IMPORTANT FIX

    else:
        st.error("Invalid username or password")