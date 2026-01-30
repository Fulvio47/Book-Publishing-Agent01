import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import json

st.set_page_config(page_title="Grimoire Agent UI", page_icon="🪄")
st.title("🪄 Grimoire Editor Agent")

# --- 1. GOOGLE AUTHENTICATION ---
try:
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_info, 
        scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
    )
    docs_service = build('docs', 'v1', credentials=creds)
    st.sidebar.success("✅ Google Systems Online")
except Exception as e:
    st.sidebar.error(f"❌ Google Setup Error: {e}")
    st.stop()

# --- 2. OPENROUTER LOGIC (No OpenAI Library Needed) ---
st.sidebar.divider()
or_key = st.sidebar.text_input("OpenRouter API Key", type="password", value=st.secrets.get("OPENROUTER_API_KEY", ""))

def call_openrouter(prompt):
    headers = {
        "Authorization": f"Bearer {or_key}",
        "HTTP-Referer": "http://localhost:8501", # Required by OpenRouter
        "Content-Type": "application/json"
    }
    data = {
        "model": "openrouter/auto", 
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, data=json.dumps(data))
    return response.json()['choices'][0]['message']['content']

# --- 3. AGENT BRAIN ---
st.subheader("🤖 Request New Revisions")
user_instruction = st.text_input("Instruction (e.g., 'Suggest 3 visceral YA metaphors for a cold room')")

if st.button("Ask Chimera"):
    if not or_key:
        st.error("Please enter your OpenRouter Key in the sidebar.")
    else:
        with st.spinner("Consulting the Grimoire..."):
            answer = call_openrouter(user_instruction)
            st.info(answer)

# --- 4. BATCH EDIT TABLE ---
st.divider()
st.subheader("📝 Batch Edit Commands")
doc_id = st.text_input("Document ID", "1VE-YIgjO33Heb7iIma2lJ23B90Rdaqq5gWsEbcfL2VE")

if 'rows' not in st.session_state:
    st.session_state.rows = [{"Find": "", "Replace With": ""}]

edit_df = st.data_editor(st.session_state.rows, num_rows="dynamic", use_container_width=True)

if st.button("🚀 Execute Batch Revisions"):
    commands = [row for row in edit_df if row["Find"].strip() != ""]
    if commands:
        with st.spinner("Writing to Doc..."):
            try:
                requests_list = []
                for cmd in commands:
                    requests_list.append({
                        'replaceAllText': {
                            'containsText': {'text': cmd["Find"], 'matchCase': True},
                            'replaceText': cmd["Replace With"]
                        }
                    })
                docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests_list}).execute()
                st.success("Revisions complete!")
                st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")
