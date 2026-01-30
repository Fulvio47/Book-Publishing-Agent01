import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import json

# --- SETUP & AUTH ---
st.set_page_config(page_title="Grimoire Agent", layout="wide")
st.title("🪄 Grimoire Editor Agent")

try:
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_info, 
        scopes=[
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
    )
    docs_service = build('docs', 'v1', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    st.sidebar.success("✅ Google Linked")
except:
    st.sidebar.error("❌ Google Secrets Missing")
    st.stop()

or_key = st.sidebar.text_input("OpenRouter Key", type="password", value=st.secrets.get("OPENROUTER_API_KEY", ""))

# --- HELPER FUNCTIONS ---
def ask_chimera(prompt):
    headers = {"Authorization": f"Bearer {or_key}", "Content-Type": "application/json"}
    # Using 'free' models via OpenRouter (Chimera/Mistral/etc)
    data = {
        "model": "openrouter/auto", 
        "messages": [{"role": "system", "content": "You are a professional YA book editor. Always suggest changes in a 'Find: [text] | Replace: [text]' format."},
                     {"role": "user", "content": prompt}]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, data=json.dumps(data))
    return response.json()['choices'][0]['message']['content']

def get_doc_text(doc_id):
    doc = docs_service.documents().get(documentId=doc_id).execute()
    content = doc.get('body').get('content')
    text = ""
    for element in content:
        if 'paragraph' in element:
            for text_run in element.get('paragraph').get('elements'):
                text += text_run.get('textRun', {}).get('content', '')
    return text

# --- UI INTERFACE ---
doc_id = st.text_input("Active Google Doc ID", "1VE-YIgjO33Heb7iIma2lJ23B90Rdaqq5gWsEbcfL2VE")

st.subheader("🤖 Chat with Chimera")
user_input = st.chat_input("Ask Chimera to analyze or rewrite a section...")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)
    
    with st.chat_message("assistant"):
        with st.spinner("Analyzing document..."):
            # 1. Fetch real content from your Doc
            current_text = get_doc_text(doc_id)[:2000] # Limit context for speed
            
            # 2. Send to Chimera
            full_prompt = f"Based on this text: '{current_text}', please fulfill this request: {user_input}"
            suggestion = ask_chimera(full_prompt)
            st.write(suggestion)
            
            st.info("💡 You can copy the Find/Replace text below into the Batch Editor to apply these changes.")

# --- BATCH EDITOR (The Pyroid3 Execution Logic) ---
st.divider()
st.subheader("📝 Batch Execution Table")
if 'table_data' not in st.session_state:
    st.session_state.table_data = [{"Find": "", "Replace": ""}]

edited_df = st.data_editor(st.session_state.table_data, num_rows="dynamic")

if st.button("🚀 Push Changes to Google Doc"):
    valid_changes = [row for row in edited_df if row["Find"]]
    if valid_changes:
        with st.spinner("Executing commands..."):
            reqs = [{'replaceAllText': {'containsText': {'text': r['Find'], 'matchCase': True}, 'replaceText': r['Replace']}} for r in valid_changes]
            docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': reqs}).execute()
            st.success("Document Updated!")
