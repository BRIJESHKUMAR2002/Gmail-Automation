import os
import base64
import json
from pathlib import Path
from typing import AnyStr, Any
import base64
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.auth
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from langchain.chains import RetrievalQA
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAIEmbeddings, OpenAI
import os

BASE_DIR = Path(__file__).resolve().parent
ChromaDb_Dir = os.path.join(BASE_DIR, "chroma_db", "chroma_db")
collection = 'collection_db'
prompt = ''
os.environ['OPENAI_API_KEY'] = 'OPENAI API KEY'


def retrieving_chroma(query: AnyStr, chroma_dir: AnyStr, collection: Any, prompt: AnyStr):
    PROMPT = PromptTemplate(
        template=prompt + """

        {context}

        Question: {question}
        Answer:
        """,
        input_variables=["context", "question"],
        # partial_variables={"format_instructions": format_instructions}
    )

    example_db = Chroma(embedding_function=OpenAIEmbeddings(), persist_directory=chroma_dir,
                        collection_name=collection)

    chain_type_kwargs = {"prompt": PROMPT}

    qa = RetrievalQA.from_chain_type(
        llm=OpenAI(),
        chain_type="stuff",
        retriever=example_db.as_retriever(),
        return_source_documents=True,
        chain_type_kwargs=chain_type_kwargs
    )
    # response = qa.run(query)
    response = qa({"query": query})
    print(response)
    return response['result'], response['source_documents']


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

def authenticate():
    """Authenticate the user and return credentials."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("cred.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def get_unread_messages():
    """Fetch unread messages from the inbox."""
    creds = authenticate()
    try:
        # Create Gmail API client
        service = build("gmail", "v1", credentials=creds)
        # Search for unread messages
        results = service.users().messages().list(userId="me", q="is:unread").execute()
        messages = results.get("messages", [])
        print(messages,'==============---------------------------')
        return messages
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

def get_message_details(message_id):
    """Get the details of a specific message."""
    creds = authenticate()
    try:
        # Create Gmail API client
        service = build("gmail", "v1", credentials=creds)
        message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        for header in headers:
            if header["name"] == "From":
                sender = header["value"]
            if header["name"] == "Subject":
                subject = header["value"]
        return sender, subject
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None, None

def send_reply(message_id, to_email, subject,response):
    """Reply to a specific email."""
    creds = authenticate()
    try:
        # Create Gmail API client
        service = build("gmail", "v1", credentials=creds)

        # Create the reply email
        message = EmailMessage()
        message.set_content(response)
        message["To"] = to_email
        message["From"] = "Enter Your Email"  # Replace with your email
        message["Subject"] = f"Re: {subject}"

        # Encode the message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Send the reply
        send_message = {"raw": encoded_message, "threadId": message_id}
        sent_message = service.users().messages().send(userId="me", body=send_message).execute()

        print(f"Reply sent successfully! Message ID: {sent_message['id']}")
    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    # Step 1: Fetch unread messages
    unread_messages = get_unread_messages()
    print(f"Found {len(unread_messages)} unread messages.")

    # Step 2: Process each unread message
    for msg in unread_messages:
        message_id = msg["id"]
        sender, subject = get_message_details(message_id)
        print(f"Replying to: {sender}, Subject: {subject}")
        respone = retrieving_chroma(subject, ChromaDb_Dir, collection, '')
        print(respone,'====================')
        #
        # # Step 3: Send a reply
        data = send_reply(message_id, sender, subject,str(respone))
