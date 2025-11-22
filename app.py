import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import time


# --- Page Configuration ---
st.set_page_config(
    page_title="Resume Screener AI",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Styles ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        background-color: #2C3E50;
        color: white;
        font-weight: bold;
    }
    .metric-box {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Functions ---

def get_pdf_text(pdf_file):
    """Extracts text from an uploaded PDF file."""
    text = ""
    try:
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    except Exception as e:
        st.error(f"Error reading PDF {pdf_file.name}: {e}")
        return None
    return text

def analyze_candidate(resume_text, job_description, api_key):
    """
    Summarizes the candidate for a recruiter.
    """
    try:
        genai.configure(api_key=api_key)
        
        # Try specific modern model first, fallback logic if needed
        model_name = 'gemini-2.5-flash'
        model = genai.GenerativeModel(model_name)
        
        # Optimized Prompt for Recruiters
        prompt = f"""
        Act as a Senior Technical Recruiter and Talent Acquisition Specialist.
        
        I will provide you with a CANDIDATE RESUME and a TARGET JOB DESCRIPTION.
        
        YOUR GOAL:
        Provide a concise, professional summary to help a hiring manager quickly decide if they should interview this candidate.
        
        OUTPUT FORMAT (Markdown):
        
        ### 📋 Executive Summary
        (3-4 sentences summarizing the candidate's experience level, main industry, and key value proposition.)
        
        ### ⭐️ Key Strengths
        * (List 3-5 top skills/achievements relevant to the Job Description)
        
        ### ⚠️ Potential Concerns
        * (List any red flags like employment gaps, job hopping, or missing key skills. If none, say "No major concerns detected.")
        
        ### 📊 Match Score: [X]/10
        (Rate the candidate's fit for the Job Description based on keywords and experience.)
        
        ---
        CANDIDATE RESUME:
        {resume_text}
        
        TARGET JOB DESCRIPTION:
        {job_description}
        """
        
        response = model.generate_content(prompt)
        return response.text
            
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return f"⚠️ **Model Error:** The AI model `{model_name}` was not found. Please try upgrading your library: `pip install --upgrade google-generativeai`"
        return f"Error processing candidate: {error_msg}"

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Recruiter Admin")
    
    api_key = st.text_input(
        "Enter Gemini API Key", 
        type="password",
        help="Required for AI processing"
    )
    
    # Debugging Tool
    if st.button("🛠 Test API Key & List Models"):
        if not api_key:
            st.error("Enter a key first.")
        else:
            try:
                genai.configure(api_key=api_key)
                models = list(genai.list_models())
                st.success("✅ API Key is working!")
                st.write("Available Models:")
                for m in models:
                    if 'generateContent' in m.supported_generation_methods:
                        st.code(m.name)
            except Exception as e:
                st.error(f"❌ Key failed: {e}")
    
    st.markdown("---")
    st.info("💡 **Tip:** Upload multiple PDFs to screen a batch of candidates at once.")

# --- Main Content ---
st.title("👥 AI Candidate Screener")
st.markdown("#### Bulk Resume Summarization & Screening Tool")

# Input Section
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Target Role")
    job_description = st.text_area(
        "Paste Job Description (Context for grading)",
        height=150,
        placeholder="Paste the JD here to grade candidates against specific requirements..."
    )

with col2:
    st.subheader("2. Upload Candidates")
    uploaded_files = st.file_uploader(
        "Upload PDF Resumes (Batch supported)", 
        type=['pdf'], 
        accept_multiple_files=True
    )

# --- Processing ---
if st.button("🔍 Screen Candidates", type="primary"):
    if not api_key:
        st.warning("Please enter your API Key in the sidebar.")
    elif not uploaded_files:
        st.warning("Please upload at least one resume.")
    elif not job_description:
        st.warning("Please enter a Job Description for context.")
    else:
        st.markdown("---")
        st.subheader(f"Processing {len(uploaded_files)} Candidates...")
        
        # Progress bar
        progress_bar = st.progress(0)
        
        for i, uploaded_file in enumerate(uploaded_files):
            with st.expander(f"📄 Candidate: {uploaded_file.name}", expanded=True):
                # Extract Text
                resume_text = get_pdf_text(uploaded_file)
                
                if resume_text:
                    # Generate Analysis
                    analysis = analyze_candidate(resume_text, job_description, api_key)
                    st.markdown(analysis)
                else:
                    st.error("Could not read PDF content.")
            
            # Update progress
            progress_bar.progress((i + 1) / len(uploaded_files))
            time.sleep(4) # Avoid hitting rate limits too hard
            
        st.success("✅ Batch Screening Complete!")