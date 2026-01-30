import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import json

# --- 1. PAGE CONFIG & UI STYLE ---
st.set_page_config(page_title="Grimoire Master Agent", layout="wide", page_icon="🔮")

# Custom CSS for a cleaner "Agent" look
st.markdown("""
    <style>
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    .stChatFloatingInputContainer { bottom: 20px; }
    </style>
    """, unsafe_allow_name_with_html=True)

# --- 2. CONNECTOR LOGIC (The Pyroid3 Brain) ---
def initialize_connectors():
    status = {"docs": False, "sheets": False, "drive": False, "openrouter": False}
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
        # Services
        docs = build('docs', 'v1', credentials=creds)
        sheets = build('sheets', 'v4', credentials=creds)
        drive = build('drive', 'v3', credentials=creds)
        
        status["docs"] = True
        status["sheets"] = True
        status["drive"] = True
        
        # OpenRouter Check
        or_key = st.secrets.get("OPENROUTER_API_KEY") or st.sidebar.text_input("OR Key", type="password")
        if or_key:
            status["openrouter"] = True
            
        return docs, sheets, drive, or_key, status
    except Exception as e:
        st.error(f"Connector Error: {e}")
        return None, None, None, None, status

docs_api, sheets_api, drive_api, OR_KEY, conn_status = initialize_connectors()

# --- 3. UI: STATUS HEADER ---
st.title("🔮 Grimoire Master Agent")
cols = st.columns(4)
with cols[0]: st.metric("Google Docs", "Connected" if conn_status["docs"] else "Offline")
with cols[1]: st.metric("Google Sheets", "Connected" if conn_status["sheets"] else "Offline")
with cols[2]: st.metric("Google Drive", "Connected" if conn_status["drive"] else "Offline")
with cols[3]: st.metric("OpenRouter", "Active" if conn_status["openrouter"] else "Missing Key")

st.divider()

# --- 4. WORKSPACE SELECTOR ---
with st.expander("📂 Workspace Configuration", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        doc_id = st.text_input("Manuscript (Doc ID)", "1VE-YIgjO33Heb7iIma2lJ23B90Rdaqq5gWsEbcfL2VE")
    with c2:
        sheet_id = st.text_input("Critique Tracker (Sheet ID)", "")

# --- 5. CHAT INTERFACE (The Brain) ---
st.subheader("🤖 Agent Chat")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Command the agent (e.g. 'Read the sheet and suggest revisions')"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Processing through Chimera..."):
            # LOGIC: If user asks to read the sheet
            context = ""
            if "read" in prompt.lower() and sheet_id:
                sheet_data = sheets_api.spreadsheets().values().get(spreadsheetId=sheet_id, range="A1:C10").execute()
                context = f"Here is the latest critique data from the sheet: {sheet_data.get('values', [])}"
            
            # Call OpenRouter
            headers = {"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "openrouter/auto",
                "messages": [
                    {"role": "system", "content": "You are a master YA editor. Use the context provided to suggest edits in 'Find | Replace' format."},
                    {"role": "user", "content": f"{context}\n\nUser Instruction: {prompt}"}
                ]
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            response_text = res.json()['choices'][0]['message']['content']
            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})

# --- 6. EXECUTION TABLE (The Hands) ---
st.divider()
st.subheader("⚡ Execution Engine")
st.caption("Paste the suggestions from the chat above into this table to execute them on the live document.")

if 'batch_data' not in st.session_state:
    st.session_state.batch_data = [{"Find": "", "Replace": ""}]

edited_df = st.data_editor(st.session_state.batch_data, num_rows="dynamic", use_container_width=True)

if st.button("🚀 Push Revisions to Google Doc"):
    actions = [row for row in edited_df if row["Find"]]
    if actions:
        with st.spinner("Updating Manuscript..."):
            bulk_req = [{'replaceAllText': {'containsText': {'text': r['Find'], 'matchCase': True}, 'replaceText': r['Replace']}} for r in actions]
            docs_api.documents().batchUpdate(documentId=doc_id, body={'requests': bulk_req}).execute()
            st.success("Revisions Applied! Manuscript Updated.")
            st.balloons()
