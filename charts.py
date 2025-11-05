import streamlit as st
import os
from datetime import datetime, timedelta
from uuid import uuid4
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

# === Environment Fix ===
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

# === Constants (copied from project files) ===
AZURE_OPENAI_KEY = "03Q78RfTsocV8O8bnFJ58F8FdJQM5MA2IgE2n3OSudWpfKTh4UWnJQQJ99ALACL93NaXJ3w3AAAAACOGWgGG"
AZURE_OPENAI_ENDPOINT = "https://happpt6262624605.openai.azure.com/"
AZURE_OPENAI_VERSION = "2024-05-01-preview"
ASSISTANT_ID = "asst_UUhSYD2kSxkP2DWOeItCVDNv"

BLOB_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=bnlwestgunileverad03650;AccountKey=3kghaUEkCr4fk4POdOGraYaYakb1m3q9RVKC6WJX1ue762J7AiNWuu9DB7RcLYen8WfLf5w3BU5e+AStRxZZ3w==;EndpointSuffix=core.windows.net"
BLOB_CONTAINER_NAME = "6p-crib-sheet-generator-input-data"
account_name = "bnlwestgunileverad03650"
account_key = "3kghaUEkCr4fk4POdOGraYaYakb1m3q9RVKC6WJX1ue762J7AiNWuu9DB7RcLYen8WfLf5w3BU5e+AStRxZZ3w=="

# initialize clients
client = AzureOpenAI(api_key=AZURE_OPENAI_KEY, api_version=AZURE_OPENAI_VERSION, azure_endpoint=AZURE_OPENAI_ENDPOINT)
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)


def generate_sas_url(account_name, container_name, blob_name, account_key, expiry_minutes=60):
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes)
    )
    return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"


def list_png_blobs():
    results = []
    try:
        for blob in container_client.list_blobs(name_starts_with=""):
            if blob.name.lower().endswith('.png'):
                url = generate_sas_url(account_name, BLOB_CONTAINER_NAME, blob.name, account_key, expiry_minutes=60)
                results.append((blob.name, url, blob.last_modified))
    except Exception as e:
        st.error(f"Failed to list blobs: {e}")
    results.sort(key=lambda x: x[2] or datetime.min, reverse=True)
    return results


def upload_blob_from_bytes(data_bytes: bytes, blob_name: str):
    try:
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(data_bytes, overwrite=True)
        return True
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return False


def generate_chart_via_assistant(query: str):
    """Send the query to the assistant, wait for run completion, collect any image_file outputs and upload them to blob storage."""
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=query)
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)

    while run.status in ["queued", "in_progress", "cancelling"]:
        time_sleep = 1
        import time
        time.sleep(time_sleep)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

    blob_names = []
    response_text = ""
    if run.status == "completed":
        latest_message = None
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for msg in sorted(messages, key=lambda m: m.created_at, reverse=True):
            if msg.role == "assistant":
                latest_message = msg
                break

        if latest_message:
            for content in latest_message.content:
                if content.type == "text":
                    response_text = content.text.value
                elif content.type == "image_file":
                    file_id = content.image_file.file_id
                    file_data = client.files.content(file_id).read()
                    blob_name = f"chart_{uuid4().hex}.png"
                    uploaded = upload_blob_from_bytes(file_data, blob_name)
                    if uploaded:
                        # generate SAS URL like in wilson_main
                        image_url = generate_sas_url(account_name, BLOB_CONTAINER_NAME, blob_name, account_key)
                        blob_names.append(blob_name)
                        # append to session messages so the chat UI can reference it (if user exists)
                        try:
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"Chart generated: {blob_name}",
                                "image_url": image_url
                            })
                        except Exception:
                            # session messages might not exist in this context — ignore
                            pass

    return response_text, blob_names


def application():
    if not st.session_state.get("authenticated", False):
        st.warning("Please login first.")
        st.stop()

    st.sidebar.title("Foresight")
    if st.sidebar.button("📊 DataPulse"):
        st.session_state.page = "datapulse"
        st.rerun()
    if st.sidebar.button("💬 Ask Foresight"):
        st.session_state.page = "wilson_main"
        st.rerun()
    if st.sidebar.button("🗂️ Chat History"):
        st.session_state.page = "wilson_chat_history"
        st.rerun()
    if st.sidebar.button("📈 ForeSight Studio"):
        st.session_state.page = "charts"
        st.rerun()
    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "login"
        st.rerun()

    st.title("📊 ForeSight Studio")
    st.write("Submit a query to the assistant to generate a chart .")

    chart_query = st.text_input("Enter a chart generation query (assistant will create the chart)", key="chart_query_input")
    if st.button("Generate Chart"):
        if not chart_query or not chart_query.strip():
            st.warning("Please enter a query to generate a chart.")
        else:
            with st.spinner("Requesting assistant to generate chart..."):
                response_text, blob_names = generate_chart_via_assistant(chart_query.strip())
                if blob_names:
                    st.success(f"Assistant generated {len(blob_names)} chart(s): {', '.join(blob_names)}")
                    # refresh the page to show newly uploaded charts
                    st.rerun()
                else:
                    st.info("No image files were returned by the assistant.\n" + (response_text or ""))

    st.markdown("---")
    st.header("Previous Charts generated")

    blobs = list_png_blobs()
    if not blobs:
        st.info("No PNG charts found in blob storage.")
        return

    cols = st.columns(2)
    for i, (name, url, modified) in enumerate(blobs):
        col = cols[i % 2]
        with col:
            st.image(url, caption=None, use_column_width=True)
            import requests
            try:
                resp = requests.get(url)
                resp.raise_for_status()
                img_bytes = resp.content
            except Exception as e:
                img_bytes = b''
            st.download_button(label="Download image", data=img_bytes, file_name=name, mime='image/png')
