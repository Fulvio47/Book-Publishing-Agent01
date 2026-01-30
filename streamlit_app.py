import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import json
import re

# --- 1. HARDCODED CONFIGURATION ---
MANUSCRIPT_ID = "1VE-YIgjO33Heb7iIma2lJ23B90Rdaqq5gWsEbcfL2VE"
LIBRARY_SHEET_ID = "1TR1Rhk4yqa57HD0dEKGOhrNq5aWxAF7LSrpM138UFPs"

st.set_page_config(page_title="Grimoire Master Agent", layout="wide")

# --- 2. AUTHENTICATION FIX ---
@st.cache_resource
def get_gcp_services():
    try:
        # Pulling directly from the key name we verified earlier
        info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            info, 
            scopes=[
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
        )
        return {
            "docs": build('docs', 'v1', credentials=creds),
            "sheets": build('sheets', 'v4', credentials=creds),
            "drive": build('drive', 'v3', credentials=creds)
        }
    except Exception as e:
        st.error(f"Authentication Failed: {e}")
        return None

services = get_gcp_services()
OR_KEY = st.secrets.get("OPENROUTER_API_KEY")

# --- 3. UI: CONNECTION STATUS ---
st.title("🔮 Grimoire Editorial Agent")
c1, c2, c3 = st.columns(3)
c1.success("📖 Manuscript Linked") if services else c1.error("📖 Manuscript Offline")
c2.success("📚 Library Linked") if services else c2.error("📚 Library Offline")
c3.success("🧠 Chimera Active") if OR_KEY else c3.error("🧠 Chimera Offline")

# --- 4. INTELLIGENCE GATHERING ---
def get_story_context():
    if not services: return ""
    # Pull first 10 rows of Library Sheet (Story Objectives)
    sheet = services["sheets"].spreadsheets().values().get(
        spreadsheetId=LIBRARY_SHEET_ID, range="A1:C20").execute()
    return str(sheet.get('values', []))

def get_manuscript_end():
    if not services: return ""
    doc = services["docs"].documents().get(documentId=MANUSCRIPT_ID).execute()
    content = doc.get('body').get('content')
    full_text = ""
    for val in content:
        if 'paragraph' in val:
            for el in val.get('paragraph').get('elements'):
                full_text += el.get('textRun', {}).get('content', '')
    # Return last 3000 chars for context
    return full_text[-3000:]

# --- 5. CHAT & GENERATION ---
tab1, tab2 = st.tabs(["✍️ Editorial Assistant", "📖 Chapter Generator"])

with tab1:
    st.subheader("Editorial Recommendations")
    instruction = st.text_area("What should the agent look for?", "Analyze the prose for 'YA-grit' and suggest 3 visceral improvements.")
    
    if st.button("Generate Recommendations"):
        context = f"STORY RULES: {get_story_context()}\n\nMANUSCRIPT: {get_manuscript_end()}"
        headers = {"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "openrouter/auto",
            "messages": [{"role": "system", "content": "You are a YA editor. Return JSON only: [{'find': '...', 'replace': '...'}]"},
                         {"role": "user", "content": f"{context}\n\nTask: {instruction}"}]
        }
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        # Parse suggestions into session state for approval
        try:
            raw_content = res.json()['choices'][0]['message']['content']
            # Simple regex to find JSON in case the model adds chatter
            json_str = re.search(r'\[.*\]', raw_content, re.DOTALL).group()
            st.session_state.pending_edits = json.loads(json_str)
        except:
            st.error("Chimera had trouble formatting the JSON. Try again.")

    # Approval Gallery
    if "pending_edits" in st.session_state:
        st.write("### Approve Changes")
        final_selections = []
        for i, edit in enumerate(st.session_state.pending_edits):
            col_a, col_b = st.columns([0.1, 0.9])
            if col_a.checkbox("Apply", key=f"edit_{i}"):
                final_selections.append(edit)
            col_b.info(f"**Find:** {edit['find']}\n\n**Replace:** {edit['replace']}")
        
        if st.button("🚀 Execute Approved Changes"):
            reqs = [{'replaceAllText': {'containsText': {'text': e['find'], 'matchCase': True}, 'replaceText': e['replace']}} for e in final_selections]
            services["docs"].documents().batchUpdate(documentId=MANUSCRIPT_ID, body={'requests': reqs}).execute()
            st.success("Revisions Pushed!")
            del st.session_state.pending_edits

with tab2:
    st.subheader("Next Chapter Generation")
    if st.button("Draft Next Chapter"):
        with st.spinner("Consulting the Grimoire Library..."):
            context = f"RULES: {get_story_context()}\n\nPREVIOUS TEXT: {get_manuscript_end()}"
            # Request Chimera to write next chapter
            # (Logic for Chapter X+1 header detection goes here)
            st.write("Chimera is drafting... [This is where the long-form text will appear]")
            # Option to 'Append to Doc' would be here
