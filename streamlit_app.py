import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import json

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Grimoire Master Agent", layout="wide", page_icon="🔮")

# Safer CSS Injection
st.markdown("### 🔮 Grimoire Master Agent")

# --- 2. CONNECTOR LOGIC ---
def check_connections():
    results = {"docs": "🔴", "sheets": "🔴", "drive": "🔴", "chimera": "🔴"}
    services = {"docs": None, "sheets": None, "drive": None}
    
    try:
        if "gcp_service_account" in st.secrets:
            info = st.secrets["gcp_service_account"]
            creds = service_account.Credentials.from_service_account_info(
                info, 
                scopes=[
                    'https://www.googleapis.com/auth/documents',
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/spreadsheets'
                ]
            )
            services["docs"] = build('docs', 'v1', credentials=creds)
            services["sheets"] = build('sheets', 'v4', credentials=creds)
            services["drive"] = build('drive', 'v3', credentials=creds)
            results["docs"], results["sheets"], results["drive"] = "🟢", "🟢", "🟢"
    except Exception as e:
        st.sidebar.error(f"Google Connection Failed: {e}")

    if st.secrets.get("OPENROUTER_API_KEY"):
        results["chimera"] = "🟢"
        
    return services, results

apis, status = check_connections()

# --- 3. STATUS HEADER ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Docs API", status["docs"])
col2.metric("Sheets API", status["sheets"])
col3.metric("Drive API", status["drive"])
col4.metric("Chimera (OR)", status["chimera"])

st.divider()

# --- 4. WORKSPACE CONFIG ---
with st.expander("📂 Workspace & File IDs", expanded=True):
    c1, c2 = st.columns(2)
    doc_id = c1.text_input("Active Manuscript (Doc ID)", "1VE-YIgjO33Heb7iIma2lJ23B90Rdaqq5gWsEbcfL2VE")
    sheet_id = c2.text_input("Critique Tracker (Sheet ID)", "")

# --- 5. CHAT COMMAND CENTER ---
st.subheader("🤖 Command Chimera")
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if user_query := st.chat_input("Ex: 'Read my sheet and suggest a rewrite for the intro'"):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.write(user_query)

    with st.chat_message("assistant"):
        with st.spinner("Agent is thinking..."):
            # Context Fetching Logic
            sheet_context = ""
            if sheet_id and status["sheets"] == "🟢":
                try:
                    res = apis["sheets"].spreadsheets().values().get(spreadsheetId=sheet_id, range="A1:C10").execute()
                    sheet_context = f"\n\nContext from Sheets: {res.get('values', [])}"
                except: pass

            # OpenRouter Call
            headers = {
                "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "openrouter/auto",
                "messages": [
                    {"role": "system", "content": "You are a YA editor. Give suggestions as 'Find: [text] | Replace: [text]'."},
                    {"role": "user", "content": f"{user_query} {sheet_context}"}
                ]
            }
            try:
                r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                ans = r.json()['choices'][0]['message']['content']
                st.write(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})
            except Exception as e:
                st.error(f"Chimera Error: {e}")

# --- 6. EXECUTION TABLE ---
st.divider()
st.subheader("⚡ Batch Execution Engine")
if 'edits' not in st.session_state:
    st.session_state.edits = [{"Find": "", "Replace": ""}]

final_df = st.data_editor(st.session_state.edits, num_rows="dynamic", use_container_width=True)

if st.button("🚀 Execute Changes on Google Doc"):
    valid = [r for r in final_df if r["Find"]]
    if valid and apis["docs"]:
        with st.spinner("Applying edits..."):
            reqs = [{'replaceAllText': {'containsText': {'text': x['Find'], 'matchCase': True}, 'replaceText': x['Replace']}} for x in valid]
            apis["docs"].documents().batchUpdate(documentId=doc_id, body={'requests': reqs}).execute()
            st.success("Revisions Pushed Successfully!")
            st.balloons()
