import streamlit as st
# Set page config here as the first Streamlit command
st.set_page_config(page_title="Sql Agent", page_icon="📄")

import login
import wilson_main

if "page" not in st.session_state:
    st.session_state.page = "login"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
page = st.session_state.page

# Session safety check: block access to internal pages if not authenticated
if page == "wilson_main" and not st.session_state.authenticated:
    st.warning("⚠️ Please log in to continue.")
    st.session_state.page = "login"
    st.rerun()

if page == "login":
    login.application()  # call login's app function to run the login UI
elif page == "wilson_main":
    wilson_main.application()
else:
    st.write("Page not found")
