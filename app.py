import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd

# 1. Setup Page and Credentials
st.set_page_config(page_title="Grimoire Agent UI", page_icon="🪄")
st.title("🪄 Grimoire Editor Agent")

# Load credentials from Streamlit Secrets
try:
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_info, 
        scopes=[
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive'
        ]
    )
    service = build('docs', 'v1', credentials=creds)
    st.sidebar.success("✅ Agent Authenticated")
except Exception as e:
    st.sidebar.error("❌ Credentials Missing in Secrets")
    st.stop()

# 2. Input Section
doc_id = st.text_input("Document ID", "1VE-YIgjO33Heb7iIma2lJ23B90Rdaqq5gWsEbcfL2VE")

st.subheader("Revision Commands")
st.write("Enter the exact text to find and the new text to insert.")

# Interactive Data Editor for Batch Processing
if 'rows' not in st.session_state:
    st.session_state.rows = [{"Find": "", "Replace With": ""}]

edit_df = st.data_editor(st.session_state.rows, num_rows="dynamic", use_container_width=True)

# 3. Execution Logic
if st.button("🚀 Execute Batch Revisions"):
    # Filter out empty rows
    commands = [row for row in edit_df if row["Find"].strip() != ""]
    
    if not commands:
        st.warning("No commands entered.")
    else:
        with st.spinner("Agent writing to Google Doc..."):
            try:
                requests = []
                for cmd in commands:
                    requests.append({
                        'replaceAllText': {
                            'containsText': {
                                'text': cmd["Find"],
                                'matchCase': True
                            },
                            'replaceText': cmd["Replace With"]
                        }
                    })
                
                # Execute batch update
                result = service.documents().batchUpdate(
                    documentId=doc_id, 
                    body={'requests': requests}
                ).execute()
                
                st.success(f"Success! {len(commands)} sections updated.")
                st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()
st.caption("Connected as: google-api-credentials@nodal-subset-485621-g1.iam.gserviceaccount.com")
