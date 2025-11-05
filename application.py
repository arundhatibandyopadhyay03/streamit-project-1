import streamlit as st
# Set page config here as the first Streamlit command
st.set_page_config(page_title="Foresight", page_icon="📄")

import login
import wilson_main
import wilson_chat_history
import charts
import datapulse

#page = st.query_params.get("page", ["login"])[0]


if "page" not in st.session_state:
    st.session_state.page = "login"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
page = st.session_state.page

# Session safety check: block access to internal pages if not authenticated
protected_pages = ["wilson_main", "wilson_chat_history", "charts", "datapulse"]
if page in protected_pages and not st.session_state.authenticated:
    st.warning("⚠️ Please log in to continue.")
    st.session_state.page = "login"
    st.rerun()
if page == "login":
    login.application()  # call login's app function to run the login UI
elif page == "wilson_main":
    wilson_main.application()
elif page == "wilson_chat_history":
    wilson_chat_history.application()
elif page == "charts":
    charts.application()
elif page == "datapulse":
    datapulse.application()
else:
    st.write("Page not found")
