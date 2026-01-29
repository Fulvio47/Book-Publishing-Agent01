import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from openai import OpenAI
import pandas as pd

st.set_page_config(page_title="Grimoire Agent UI", page_icon="🪄")
st.title("🪄 Grimoire Editor Agent (OpenRouter Powered)")

# --- 1. AUTHENTICATION (Google & OpenRouter) ---
try:
    # Google Docs Auth
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_info, 
        scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
    )
    docs_service = build('docs', 'v1', credentials=creds)
    
    # OpenRouter Auth
    client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=st.secrets["OPENROUTER_API_KEY"],
    )
    st.sidebar.success("✅ Systems Online")
except Exception as e:
    st.sidebar.error(f"❌ Setup Error: {e}")
    st.stop()

# --- 2. AGENT BRAIN (Chimera/OpenRouter) ---
st.subheader("🤖 Request New Revisions")
user_instruction = st.text_input("Tell the agent what to change (e.g., 'Make the dialogue in the library punchier')")

if st.button("Generate Suggestions"):
    with st.spinner("Chimera is analyzing your prose..."):
        # This calls OpenRouter using the OpenAI library format
        completion = client.chat.completions.create(
          model="openrouter/auto", # Or specify a specific Chimera model
          messages=[{"role": "user", "content": user_instruction}]
        )
        st.write("### Suggestions:")
        st.info(completion.choices[0].message.content)

# --- 3. MANUAL REVISION TABLE ---
st.divider()
st.subheader("📝 Batch Edit Commands")
doc_id = st.text_input("Document ID", "1VE-YIgjO33Heb7iIma2lJ23B90Rdaqq5gWsEbcfL2VE")

if 'rows' not in st.session_state:
    st.session_state.rows = [{"Find": "", "Replace With": ""}]

edit_df = st.data_editor(st.session_state.rows, num_rows="dynamic", use_container_width=True)

if st.button("🚀 Execute Batch Revisions"):
    commands = [row for row in edit_df if row["Find"].strip() != ""]
    if commands:
        with st.spinner("Agent writing to Google Doc..."):
            try:
                requests = []
                for cmd in commands:
                    requests.append({
                        'replaceAllText': {
                            'containsText': {'text': cmd["Find"], 'matchCase': True},
                            'replaceText': cmd["Replace With"]
                        }
                    })
                docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
                st.success("Document updated successfully!")
                st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")
