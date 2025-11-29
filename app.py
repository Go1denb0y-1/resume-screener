import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import pandas as pd
import json
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="Resume Screener Pro",
    page_icon="🚀",
    layout="wide"
)

# --- ACCESS CONTROL ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["ACCESS_CODE"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 Enter Access Code:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 Enter Access Code:", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- API SETUP ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("Secrets missing.")
    st.stop()

# --- FUNCTIONS ---
def get_pdf_text(pdf_file):
    text = ""
    try:
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    except:
        return None
    return text

def analyze_candidate_json(resume_text, job_description):
    """Asks Gemini for a JSON response to allow sorting/filtering."""
    model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
    
    prompt = f"""
    Act as a Technical Recruiter. Analyze this resume against the JD.
    Return a valid JSON object with these exact keys:
    {{
        "candidate_name": "Name or 'Unknown'",
        "match_score": 0,  // Integer 0-100
        "years_experience": "Estimate from text",
        "key_skills": ["Skill1", "Skill2", "Skill3"],
        "summary": "2 sentence executive summary",
        "red_flags": "Any concerns or 'None'",
        "email_draft": "Write a short email to the candidate inviting them for an interview"
    }}

    RESUME: {resume_text}
    JOB DESC: {job_description}
    """
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        return None

# --- UI LAYOUT ---
st.title("🚀 Resume Screener Pro")
st.markdown("#### The Leaderboard Edition")

# Session State to hold results so they don't disappear on refresh
if 'results_data' not in st.session_state:
    st.session_state['results_data'] = []

col1, col2 = st.columns([1, 2])

with col1:
    st.info("1. Setup Job Context")
    job_description = st.text_area("Paste Job Description", height=200, placeholder="Paste JD here...")
    
with col2:
    st.info("2. upload Candidates")
    uploaded_files = st.file_uploader("Upload Resumes (PDF)", type=['pdf'], accept_multiple_files=True)
    
    if st.button("Start Analysis", type="primary"):
        if not uploaded_files or not job_description:
            st.warning("Missing files or JD.")
        else:
            st.session_state['results_data'] = [] # Reset
            progress_bar = st.progress(0)
            status = st.empty()
            
            for i, file in enumerate(uploaded_files):
                status.text(f"Analyzing {file.name}...")
                text = get_pdf_text(file)
                
                if text:
                    data = analyze_candidate_json(text, job_description)
                    if data:
                        data['filename'] = file.name # Add filename for reference
                        st.session_state['results_data'].append(data)
                
                progress_bar.progress((i + 1) / len(uploaded_files))
                time.sleep(4) # Rate limit safety
            
            status.success("Analysis Complete!")

# --- DISPLAY RESULTS (The Upgrade) ---
if st.session_state['results_data']:
    st.divider()
    st.subheader("🏆 Candidate Leaderboard")
    
    # Create DataFrame
    df = pd.DataFrame(st.session_state['results_data'])
    
    # Reorder columns for neatness
    display_cols = ['candidate_name', 'match_score', 'years_experience', 'red_flags', 'filename']
    
    # Show Sortable Table
    st.dataframe(
        df[display_cols].sort_values(by='match_score', ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "match_score": st.column_config.ProgressColumn(
                "Match Score", format="%d", min_value=0, max_value=100
            ),
        }
    )
    
    # Download Button (The "Money" Feature)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download Report (CSV)",
        csv,
        "recruitment_report.csv",
        "text/csv",
        key='download-csv'
    )
    
    # Detailed View
    st.divider()
    st.subheader("📝 Detailed Breakdown")
    
    for candidate in st.session_state['results_data']:
        with st.expander(f"{candidate['match_score']}% - {candidate['candidate_name']}"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Experience:** {candidate['years_experience']}")
                st.write(f"**Skills:** {', '.join(candidate['key_skills'])}")
            with c2:
                st.write(f"**Summary:** {candidate['summary']}")
                st.error(f"**Red Flags:** {candidate['red_flags']}")
            
            st.text_area("Draft Email", candidate['email_draft'], height=100)

