
import os
from dotenv import load_dotenv


def load_env_config():
    """Load configuration from environment variables"""
    return {
        "AZURE_OPENAI_KEY": os.getenv("AZURE_OPENAI_KEY"),
        "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "AZURE_OPENAI_VERSION": os.getenv("AZURE_OPENAI_VERSION"),
        "ASSISTANT_ID": os.getenv("ASSISTANT_ID"),
        "BLOB_CONNECTION_STRING": os.getenv("BLOB_CONNECTION_STRING"),
        "BLOB_CONTAINER_NAME": os.getenv("BLOB_CONTAINER_NAME"),
        "COSMOS_ENDPOINT": os.getenv("COSMOS_ENDPOINT"),
        "COSMOS_KEY": os.getenv("COSMOS_KEY"),
        "COSMOS_DB_NAME": os.getenv("COSMOS_DB_NAME"),
        "COSMOS_CONTAINER_NAME": os.getenv("COSMOS_CONTAINER_NAME"),
        "account_name": os.getenv("STORAGE_ACCOUNT_NAME"),
        "account_key": os.getenv("STORAGE_ACCOUNT_KEY"),
    }