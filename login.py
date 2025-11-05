# login.py
import streamlit as st
import os

def get_valid_users():
    """Load user credentials from Streamlit secrets or environment variables"""
    try:
        # Try Streamlit secrets first (for cloud deployment)
        return dict(st.secrets["auth"])
    except (KeyError, FileNotFoundError):
        # Fallback to environment variables (for local development)
        return {
            "user1": os.getenv("AUTH_USER1", "password1"),
            "admin": os.getenv("AUTH_ADMIN", "admin123"),
            "john": os.getenv("AUTH_JOHN", "doe456"),
            "dev": os.getenv("AUTH_DEV", "admin"),
        }

VALID_USERS = get_valid_users()

def application():
    
    
    # Custom title with center alignment and increased font size
    st.markdown("""
        <h1 style='text-align: center; font-size: 50px;'>Sql Agent
 </h1>
        <h3 style='text-align: center;'>
 </h3>
    """, unsafe_allow_html=True)
    # st.title("✨Wilson")
    # st.subheader("Turn your logistics data into decisions with Wilson")
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = ""

    

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in VALID_USERS and VALID_USERS[username] == password:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.success("✅ Login successful")
            #st.experimental_set_query_params(page="main_wilson")
            #st.query_params["page"] = "wilson_main"
             # 👇 Set flag to reset thread in wilson_main
            st.session_state.just_logged_in = True
            st.session_state.page = "wilson_main"
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

