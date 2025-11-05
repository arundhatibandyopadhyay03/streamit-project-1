import streamlit as st
import time
import os
from uuid import uuid4
from datetime import datetime
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, PartitionKey
from PIL import Image

# === Environment Fix ===
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

# === Constants (Replace with your actual credentials) ===
VALID_USERS = {"user1": "password1", "admin": "admin123","dev":"admin"}
# === Constants ===
AZURE_OPENAI_KEY = "03Q78RfTsocV8O8bnFJ58F8FdJQM5MA2IgE2n3OSudWpfKTh4UWnJQQJ99ALACL93NaXJ3w3AAAAACOGWgGG"
AZURE_OPENAI_ENDPOINT = "https://happpt6262624605.openai.azure.com/"
AZURE_OPENAI_VERSION = "2024-05-01-preview"
ASSISTANT_ID = "asst_UUhSYD2kSxkP2DWOeItCVDNv"

BLOB_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=bnlwestgunileverad03650;AccountKey=3kghaUEkCr4fk4POdOGraYaYakb1m3q9RVKC6WJX1ue762J7AiNWuu9DB7RcLYen8WfLf5w3BU5e+AStRxZZ3w==;EndpointSuffix=core.windows.net"
BLOB_CONTAINER_NAME = "6p-crib-sheet-generator-input-data"

COSMOS_ENDPOINT = "https://bnlweaf01q930626hp01cosmosdbwilson01.documents.azure.com:443/"
COSMOS_KEY = "3jFbeNzmrZWGSBKiwJiKC64ypNHDTSZU81NPnacjrYuolNj9dL52l0ekVMYeGIzwxP2Pr1e60CYlACDbYy42sg=="
COSMOS_DB_NAME = "Wilson"
COSMOS_CONTAINER_NAME = "wilson_chat_history"

account_name = "bnlwestgunileverad03650"
account_key = "3kghaUEkCr4fk4POdOGraYaYakb1m3q9RVKC6WJX1ue762J7AiNWuu9DB7RcLYen8WfLf5w3BU5e+AStRxZZ3w=="

# === Initialize Clients ===
client = AzureOpenAI(api_key=AZURE_OPENAI_KEY, api_version=AZURE_OPENAI_VERSION, azure_endpoint=AZURE_OPENAI_ENDPOINT)
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)
cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
db = cosmos_client.create_database_if_not_exists(id=COSMOS_DB_NAME)
container = db.create_container_if_not_exists(id=COSMOS_CONTAINER_NAME, partition_key=PartitionKey(path="/id"))

# === Logout ===
def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.page = "login"
    st.rerun()

# === Cosmos DB Chat Functions ===
def load_chat_histories(user_id):
    query = f"SELECT * FROM c WHERE c.userId = '{user_id}' ORDER BY c.timestamp DESC"
    return list(container.query_items(query=query, enable_cross_partition_query=True))

def update_chat_title(chat_id, new_title):
    item = container.read_item(item=chat_id, partition_key=chat_id)
    item['title'] = new_title
    container.replace_item(item=chat_id, body=item)

def delete_chat_history(chat_id):
    container.delete_item(item=chat_id, partition_key=chat_id)

# === Streamlit App ===
def application():
    if not st.session_state.get("authenticated", False):
        st.warning("Please login first.")
        st.stop()

    user_id = st.session_state.username
    st.title(f"Foresight Chat History - User: {user_id}")
    if st.sidebar.button("📊 DataPulse"):
        st.session_state.page = "datapulse"
        st.rerun()
    if st.sidebar.button("💬 Ask Foresight"):
        st.session_state.page = "wilson_main"
        st.rerun()
    if st.sidebar.button(" Logout"):
        logout()
    if st.sidebar.button("📈 ForeSight Studio"):
        st.session_state.page = "charts"
        st.rerun()

    chat_histories = load_chat_histories(user_id)

    # --- Filters ---
    with st.sidebar.expander("🔍 Filter Chats"):
        filter_keyword = st.text_input("Keyword in title or messages")
        filter_date_from = st.date_input("Date from")
        filter_date_to = st.date_input("Date to")

    def filter_chats(chats, keyword, date_from, date_to):
        result = []
        for chat in chats:
            chat_date = datetime.fromisoformat(chat['timestamp']).date()
            if date_from and chat_date < date_from:
                continue
            if date_to and chat_date > date_to:
                continue
            if keyword:
                keyword_lower = keyword.lower()
                title = chat.get('title', '')
                messages = chat.get('messages', [])
                if keyword_lower not in title.lower() and not any(keyword_lower in msg.get('content', '').lower() for msg in messages):
                    continue
            result.append(chat)
        return result

    filtered_chats = filter_chats(chat_histories, filter_keyword, filter_date_from, filter_date_to)

    # --- Sidebar Session List ---
    st.sidebar.markdown("### 🕘 Your Chat Sessions")
    chat_options = []
    chat_map = {}

    for i, chat in enumerate(filtered_chats):
        display_title = chat.get('title', chat['timestamp'])
        label = f"{i+1}. {display_title} ({chat['timestamp'][:10]})"
        chat_options.append(label)
        chat_map[label] = chat

    selected_chat = st.sidebar.radio("Select a chat session", options=chat_options) if chat_options else None

    if not selected_chat:
        st.sidebar.info("No chats available.")
        st.info("Select a chat session from the sidebar to view messages.")
        return

    selected_chat_data = chat_map[selected_chat]
    original_title = selected_chat_data.get('title', '')
    new_title = st.sidebar.text_input("✏️ Edit Chat Title", value=original_title)

    if st.sidebar.button("Save Title", disabled=(new_title.strip() == original_title.strip())):
        if new_title.strip():
            update_chat_title(selected_chat_data['id'], new_title.strip())
            st.sidebar.success("Title updated!")
            st.rerun()
        else:
            st.sidebar.error("Title cannot be empty.")

    if st.sidebar.checkbox("Confirm deletion", key="confirm_delete"):
        if st.sidebar.button("🗑️ Delete Chat"):
            delete_chat_history(selected_chat_data['id'])
            st.sidebar.success("Chat deleted!")
            st.rerun()

    # --- Display Chat Messages ---
    st.markdown("## 📜 Chat History (Read-Only)")
    for msg in selected_chat_data.get("messages", []):
        with st.chat_message(msg.get("role", "user")):
            st.write(msg.get("content", ""))

    if st.button("New Chat"):
        st.session_state.page = "wilson_main"
        st.rerun()

