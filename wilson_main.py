import streamlit as st
import time
import os
from uuid import uuid4
from datetime import datetime,timedelta
from openai import AzureOpenAI
from azure.storage.blob import (
    BlobServiceClient,
    generate_blob_sas,
    BlobSasPermissions
)
from azure.cosmos import CosmosClient, PartitionKey
from PIL import Image
import hashlib

# === Environment Fix ===
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

# === Load Configuration from Streamlit Secrets or Environment Variables ===
def get_config():
    """Load configuration from Streamlit secrets or environment variables"""
    try:
        # Try Streamlit secrets first (for cloud deployment)
        return {
            "AZURE_OPENAI_KEY": st.secrets["azure_openai"]["key"],
            "AZURE_OPENAI_ENDPOINT": st.secrets["azure_openai"]["endpoint"],
            "AZURE_OPENAI_VERSION": st.secrets["azure_openai"]["version"],
            "ASSISTANT_ID": st.secrets["azure_openai"]["assistant_id"],
            "BLOB_CONNECTION_STRING": st.secrets["azure_storage"]["connection_string"],
            "BLOB_CONTAINER_NAME": st.secrets["azure_storage"]["container_name"],
            "COSMOS_ENDPOINT": st.secrets["azure_cosmos"]["endpoint"],
            "COSMOS_KEY": st.secrets["azure_cosmos"]["key"],
            "COSMOS_DB_NAME": st.secrets["azure_cosmos"]["database_name"],
            "COSMOS_CONTAINER_NAME": st.secrets["azure_cosmos"]["container_name"],
            "account_name": st.secrets["azure_storage"]["account_name"],
            "account_key": st.secrets["azure_storage"]["account_key"],
        }
    except (KeyError, FileNotFoundError):
        # Fallback to environment variables (for local development)
        from config import load_env_config
        return load_env_config()

# Load configuration
config = get_config()

# === Constants ===
AZURE_OPENAI_KEY = config["AZURE_OPENAI_KEY"]
AZURE_OPENAI_ENDPOINT = config["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_VERSION = config["AZURE_OPENAI_VERSION"]
ASSISTANT_ID = config["ASSISTANT_ID"]

BLOB_CONNECTION_STRING = config["BLOB_CONNECTION_STRING"]
BLOB_CONTAINER_NAME = config["BLOB_CONTAINER_NAME"]

COSMOS_ENDPOINT = config["COSMOS_ENDPOINT"]
COSMOS_KEY = config["COSMOS_KEY"]
COSMOS_DB_NAME = config["COSMOS_DB_NAME"]
COSMOS_CONTAINER_NAME = config["COSMOS_CONTAINER_NAME"]

account_name = config["account_name"]
account_key = config["account_key"]

# === Initialize Clients ===
client = AzureOpenAI(api_key=AZURE_OPENAI_KEY, api_version=AZURE_OPENAI_VERSION, azure_endpoint=AZURE_OPENAI_ENDPOINT)
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)
cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
db = cosmos_client.create_database_if_not_exists(id=COSMOS_DB_NAME)
container = db.create_container_if_not_exists(id=COSMOS_CONTAINER_NAME, partition_key=PartitionKey(path="/userId"))




# === Helper Functions ===
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

blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
blob_container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.page = "login"
    st.rerun()

def save_chat_history(user_id, thread_id, messages, title=None, uploaded_files=None):
    query = f"SELECT * FROM c WHERE c.userId = @userId AND c.threadId = @threadId"
    parameters = [
        {"name": "@userId", "value": user_id},
        {"name": "@threadId", "value": thread_id}
    ]
    items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    timestamp = datetime.utcnow().isoformat()
    title = title or timestamp

    if items:
        # Update existing document
        existing_doc = items[0]
        existing_doc["messages"] = messages
        existing_doc["timestamp"] = timestamp
        existing_doc["title"] = title
        if uploaded_files:
            existing_doc["uploaded_files"] = uploaded_files
        container.replace_item(item=existing_doc, body=existing_doc)
    else:
        # Create new document
        item_id = hashlib.sha256(f"{user_id}-{thread_id}".encode()).hexdigest()
        doc_data = {
            "id": item_id,
            "userId": user_id,
            "threadId": thread_id,
            "timestamp": timestamp,
            "title": title,
            "messages": messages
        }
        if uploaded_files:
            doc_data["uploaded_files"] = uploaded_files
        container.upsert_item(doc_data)

def upload_files_to_thread(uploaded_files, thread_id):
    """Upload files to OpenAI and return their IDs"""
    uploaded_file_ids = []
    if not uploaded_files:
        return uploaded_file_ids
    
    for uploaded_file in uploaded_files:
        try:
            # Upload file to OpenAI
            file_obj = client.files.create(
                file=uploaded_file,
                purpose="assistants"
            )
            uploaded_file_ids.append(file_obj.id)
            st.success(f"✅ Uploaded: {uploaded_file.name}")
        except Exception as e:
            st.error(f"❌ Failed to upload {uploaded_file.name}: {str(e)}")
    
    return uploaded_file_ids

def get_thread_files(thread_id):
    """Get list of files attached to the thread (from session state)"""
    try:
        # Prefer session state since we control uploads
        return st.session_state.get("uploaded_file_ids", [])
    except Exception as e:
        st.error(f"Error retrieving thread files: {str(e)}")
    return []

def display_uploaded_files(thread_id):
    """Display currently uploaded files in the thread"""
    file_ids = get_thread_files(thread_id)
    if file_ids:
        st.sidebar.subheader("📁 Uploaded Files")
        for file_id in file_ids:
            try:
                file_info = client.files.retrieve(file_id)
                st.sidebar.text(f"• {file_info.filename}")
            except Exception as e:
                st.sidebar.text(f"• File ID: {file_id}")

def send_query_with_files(client, thread_id, user_query, file_ids):
    """Send user query and attach files in batches of 10"""
    for i in range(0, len(file_ids), 10):
        batch = file_ids[i:i+10]
        attachments = [{"file_id": fid, "tools": [{"type": "file_search"}]} 
                      for fid in batch]
        
        if i == 0:
            content = user_query + " Please use the uploaded files for context."
        else:
            content = "Additional context files attached."
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content,
            attachments=attachments
        )


def application():
    image_url = None
    # Sidebar Buttons
    st.sidebar.title("Sql Agent")
    
    if st.sidebar.button("🚪 Logout"):
        logout()
    st.title("✨Sql Agent")
    st.subheader("Your AI-powered assistant for smarter, faster business insights")

    user_id = st.session_state.get("username")
    if not user_id:
        st.error("User not authenticated. Please login.")
        return

    # Initialize conversation thread
    if "thread_id" not in st.session_state:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id

    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "uploaded_file_ids" not in st.session_state:
        st.session_state.uploaded_file_ids = []

    # File Upload Section
    st.subheader("📎 Upload Files")
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        type=['pdf', 'docx', 'xlsx', 'csv', 'txt', 'pptx', 'json', 'md'],
        accept_multiple_files=True,
        help="Upload documents that the assistant can search through and reference"
    )

    # Upload button
    if uploaded_files and st.button("🔄 Upload Files to Conversation"):
        with st.spinner("Uploading files..."):
            new_file_ids = upload_files_to_thread(uploaded_files, st.session_state.thread_id)
            st.session_state.uploaded_file_ids.extend(new_file_ids)
            # Save updated file list to chat history
            save_chat_history(
                user_id, 
                st.session_state.thread_id, 
                st.session_state.messages,
                uploaded_files=st.session_state.uploaded_file_ids
            )

    # Display currently uploaded files
    display_uploaded_files(st.session_state.thread_id)

    # Add option to clear files
    if st.sidebar.button("🗑️ Clear All Files"):
        try:
            # Clear uploaded file IDs from session state
            st.session_state.uploaded_file_ids = []
            st.success("✅ All files cleared from conversation.")
            st.rerun()
        except Exception as e:
            st.error(f"Error clearing files: {str(e)}")

    st.divider()

    # Display previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("image_url"):
                st.image(msg["image_url"], caption="Generated Image", width=350)

    user_query = st.chat_input("Ask Sql Agent...")

    if user_query:
        st.chat_message("user").markdown(user_query)
        st.session_state.messages.append({"role": "user", "content": user_query})

        # Send message with or without file attachments
        if not st.session_state.uploaded_file_ids:
            client.beta.threads.messages.create(
                thread_id=st.session_state.thread_id, 
                role="user", 
                content=user_query
            )
        else:
            send_query_with_files(
                client,
                st.session_state.thread_id,
                user_query,
                st.session_state.uploaded_file_ids
            )

        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id, 
            assistant_id=ASSISTANT_ID,
            tools=[{"type": "file_search"}]  # Enable file search tool
        )

        # Show spinner while processing
        with st.spinner("Processing your request..."):
            while run.status in ["queued", "in_progress", "cancelling"]:
                time.sleep(1)
                run = client.beta.threads.runs.retrieve(thread_id=st.session_state.thread_id, run_id=run.id)

        if run.status == "completed":
            latest_message = None
            messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)

            # Find the most recent assistant message
            for msg in sorted(messages, key=lambda m: m.created_at, reverse=True):
                if msg.role == "assistant":
                    latest_message = msg
                    break

            if latest_message:
                response_text = ""
                image_url = None
                blob_names = []

                for content in latest_message.content:
                    if content.type == "text":
                        response_text = content.text.value

                        if content.text.annotations:
                            for annotation in content.text.annotations:
                                if hasattr(annotation, 'file_path') and annotation.file_path:
                                    file_id = annotation.file_path.file_id
                                    file_metadata = client.files.retrieve(file_id)
                                    file_name = file_metadata.filename
                                    ext = file_name.split('.')[-1].lower()

                                    if ext in ("csv", "xlsx", "pptx", "docx", "pdf"):
                                        file_data = client.files.content(file_id).read()
                                        blob_name = f"assistant_data_{uuid4()}.{ext}"
                                        blob_client = container_client.get_blob_client(blob_name)
                                        blob_client.upload_blob(file_data, overwrite=True)
                                        blob_names.append(blob_name)

                    elif content.type == "image_file":
                        file_id = content.image_file.file_id
                        file_data = client.files.content(file_id).read()
                        filename = f"image_{uuid4().hex}.png"
                        blob_client = blob_container_client.get_blob_client(filename)
                        blob_client.upload_blob(file_data, overwrite=True)
                        image_url = generate_sas_url(account_name, BLOB_CONTAINER_NAME, filename, account_key)
                print("response text:",response_text)
                trigger_phrase = "You can download it using the link below:"
                if trigger_phrase in response_text:
                    response_text = response_text.split(trigger_phrase)[0] + trigger_phrase
                print("response text processed:",response_text)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "image_url": image_url
                })

                with st.chat_message("assistant"):
                    st.markdown(response_text)
                    if image_url:
                        st.image(image_url, caption="Generated Image", width=350)

                    for blob_name in blob_names:
                        blob_client = container_client.get_blob_client(blob=blob_name)
                        if blob_client.exists():
                            blob_data = blob_client.download_blob().readall()
                            content_type = blob_client.get_blob_properties().content_settings.content_type
                            st.download_button(
                                label=f"📎 Download {blob_name}",
                                data=blob_data,
                                file_name=blob_name,
                                mime=content_type
                            )
                        else:
                            st.warning(f"⚠️ Blob not found: {blob_name}")
        elif run.status == "failed":
            st.chat_message("assistant").write(f"❌ Assistant failed: {run.last_error}")
        else:
            st.chat_message("assistant").write("❌ Assistant failed to respond.")

        # Save chat history after each interaction
        save_chat_history(
            user_id, 
            st.session_state.thread_id, 
            st.session_state.messages,
            uploaded_files=st.session_state.uploaded_file_ids
        )
