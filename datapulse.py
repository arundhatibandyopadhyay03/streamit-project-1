import streamlit as st
from datetime import datetime

def application():
    # Page title and button
    st.sidebar.title("Sql Agent")
    if st.sidebar.button("📊 DataPulse"):
        st.session_state.page = "datapulse"
        st.rerun()
    if st.sidebar.button("💬 Ask Sql Agent"):
        st.session_state.page = "wilson_main"
        st.rerun()
    if st.sidebar.button("🗂️ Chat History"):
        st.session_state.page = "wilson_chat_history"
        st.rerun()
    if st.sidebar.button("📈 Sql AgentStudio"):
        st.session_state.page = "charts"
        st.rerun()
    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "login"
        st.rerun()

    st.title("DataPulse")

    # Session state for alerts
    if "alerts" not in st.session_state:
        st.session_state.alerts = []

    # Add Alert button and popup (form)
    if "show_add_alert" not in st.session_state:
        st.session_state.show_add_alert = False
    if st.button("+ Add Alert"):
        st.session_state.show_add_alert = True
    if st.session_state.show_add_alert:
        with st.form("add_alert_form", clear_on_submit=False):
            st.markdown("<h2 style='color:#1A73E8;'>Add Alert</h2>", unsafe_allow_html=True)
            st.markdown("<span style='color:red;'>* indicates Mandatory field</span>", unsafe_allow_html=True)
            select_all = st.toggle("Select All Countries (Global)")
            kpi = st.selectbox("KPI *", ["", "Sales", "Profit", "Volume"])
            region = st.selectbox("Region", ["", "Asia", "Europe", "Americas"])
            sub_region = st.selectbox("Sub-Region", ["", "South Asia", "East Asia", "Western Europe"])
            cluster = st.selectbox("Cluster", ["", "Cluster 1", "Cluster 2"])
            country = st.selectbox("Country", ["", "India", "China", "UK", "USA"])
            condition = st.selectbox("Condition *", ["", ">", "<", "=", ">=", "<="])
            value = st.text_input("Value *")
            email = st.text_input("Email Id(s) *")
            subject = st.text_input("Subject")
            message = st.text_area("Message")
            submitted = st.form_submit_button("Create Alert")
            cancelled = st.form_submit_button("Cancel")
            if submitted:
                st.session_state.alerts.append({
                    "KPI": kpi,
                    "Country": country,
                    "Condition": condition,
                    "Value": value,
                    "Email": email,
                    "Message": message
                })
                st.session_state.show_add_alert = False
                st.rerun()
            if cancelled:
                st.session_state.show_add_alert = False
                st.rerun()

    # Table header (no dropdowns)
    st.markdown("""
        <div style='margin-top:24px;'>
        <table style='width:100%; border-radius:16px; background:#eaf2fb;'>
            <tr style='font-weight:bold; color:#1A73E8; font-size:22px;'><td colspan='7' style='text-align:left;padding:16px 0 0 32px;'>DataPulse</td></tr>
            <tr style='font-weight:bold; color:#1A73E8; font-size:18px;'>
                <td style='padding:8px;'>KPI</td>
                <td style='padding:8px;'>Country</td>
                <td style='padding:8px;'>Condition</td>
                <td style='padding:8px;'>Value</td>
                <td style='padding:8px;'>Email</td>
                <td style='padding:8px;'>Message</td>
                <td style='padding:8px;'>Actions</td>
            </tr>
    """, unsafe_allow_html=True)
    # Table rows
    if st.session_state.alerts:
        for alert in st.session_state.alerts:
            st.markdown(f"""
                <tr style='background:#fff;'>
                    <td style='padding:8px;'>{alert['KPI']}</td>
                    <td style='padding:8px;'>{alert['Country']}</td>
                    <td style='padding:8px;'>{alert['Condition']}</td>
                    <td style='padding:8px;'>{alert['Value']}</td>
                    <td style='padding:8px;'>{alert['Email']}</td>
                    <td style='padding:8px;'>{alert['Message']}</td>
                    <td style='padding:8px;'><button disabled style='background:#e0e0e0;border:none;padding:6px 16px;border-radius:8px;color:#888;'>Delete</button></td>
                </tr>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <tr><td colspan='7' style='text-align:center; color:#444; padding:32px;'>No records found</td></tr>
        """, unsafe_allow_html=True)
    st.markdown("</table></div>", unsafe_allow_html=True)
