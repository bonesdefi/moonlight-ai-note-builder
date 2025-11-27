"""
Moonlight AI Note Builder
Clinical documentation assistant for therapy sessions.

Audio → Transcription → SOAP Note → Validation

Single-file version - all code in one file for easy deployment.
"""

import streamlit as st
import os
import json
import asyncio
import httpx
from dotenv import load_dotenv
from datetime import datetime
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# API Keys (hardcoded for demo - move to .env for production)
# API Keys are loaded from .env file

# ============================================================
# TRANSCRIPTION MODULE
# ============================================================

async def transcribe_audio(audio_bytes: bytes, mimetype: str = "audio/wav") -> dict:
    """Transcribe audio bytes using Deepgram's API."""
    from deepgram import DeepgramClient, PrerecordedOptions
    
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise ValueError("DEEPGRAM_API_KEY environment variable not set")
    
    deepgram = DeepgramClient(api_key)
    
    # Use lower-level client to set timeout
    client = deepgram.listen.asyncprerecorded.v("1")
    url = f"{client.config.url}/v1/listen"
    
    options = PrerecordedOptions(
        model="nova-2",
        smart_format=True,
        punctuate=True,
        diarize=True,
        utterances=True,
    )
    
    # Convert options to dict
    options_dict = json.loads(options.to_json())
    
    # Increase timeout to 5 minutes (300s) for large files
    response_json = await client.post(
        url, 
        options=options_dict, 
        content=audio_bytes,
        timeout=httpx.Timeout(300.0, connect=10.0)
    )
    
    response_data = json.loads(response_json)
    
    transcript = response_data['results']['channels'][0]['alternatives'][0]['transcript']
    confidence = response_data['results']['channels'][0]['alternatives'][0]['confidence']
    
    return {"transcript": transcript, "confidence": confidence}


def transcribe_audio_sync(audio_bytes: bytes, mimetype: str = "audio/wav") -> dict:
    """Synchronous wrapper for transcription."""
    return asyncio.run(transcribe_audio(audio_bytes, mimetype))


# ============================================================
# SOAP NOTE GENERATOR
# ============================================================

class SOAPNote(BaseModel):
    """Structured SOAP note model."""
    client_name: str = Field(description="Client's name or identifier")
    session_date: str = Field(description="Date of the session")
    session_length: str = Field(description="Duration of the session")
    subjective: str = Field(description="Client's reported symptoms, feelings, and concerns")
    objective: str = Field(description="Clinician's observations during the session")
    assessment: str = Field(description="Clinical assessment and analysis")
    plan: str = Field(description="Treatment plan and next steps")
    clinical_tone: str = Field(default="Not specified", description="Overall clinical tone/presentation")
    is_complete: bool = Field(default=False)
    validation_notes: list = Field(default_factory=list)


SOAP_SYSTEM_PROMPT = """You are an experienced clinical documentation specialist at a substance abuse treatment center. Your role is to generate accurate, professional SOAP notes from therapy session transcripts.

IMPORTANT GUIDELINES:
1. Use professional clinical terminology while maintaining warmth and person-centered language
2. Never fabricate information - only document what is clearly stated or observed in the transcript
3. If information is unclear or missing, note it as "Not documented in session"
4. Be specific about substance use history, triggers, and recovery progress when mentioned
5. Include relevant recovery milestones (clean time, meeting attendance, sponsor contact) when discussed
6. Document emotional states accurately - people in recovery deserve to have their experiences validated
7. Keep notes concise but thorough enough for insurance documentation requirements

SOAP FORMAT:
- Subjective: What the client reports - their feelings, concerns, symptoms, and experiences in their own words
- Objective: Observable data - appearance, behavior, affect, speech patterns, engagement level
- Assessment: Your clinical interpretation - progress toward goals, risk factors, strengths observed
- Plan: Next steps - homework, referrals, follow-up appointments, treatment adjustments

Extract the client name, session date, and session length if mentioned. If not explicitly stated, note as "Not specified in transcript."
"""


def generate_soap_note(transcript: str, additional_context: str = "") -> SOAPNote:
    """Generate a SOAP note from a session transcript."""
    from anthropic import Anthropic
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    client = Anthropic(api_key=api_key)
    
    user_prompt = f"""Please generate a SOAP note from the following therapy session transcript.

{f"Additional Context: {additional_context}" if additional_context else ""}

TRANSCRIPT:
{transcript}

Respond with a JSON object containing these exact fields:
- client_name (string): Client's name or "Not specified"
- session_date (string): Session date or "Not specified"  
- session_length (string): Duration or "Not specified"
- subjective (string): Client's reported experience
- objective (string): Clinician observations
- assessment (string): Clinical assessment
- plan (string): Treatment plan
- clinical_tone (string): Brief description of client's overall presentation

Return ONLY valid JSON, no other text."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SOAP_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )
    
    response_text = response.content[0].text
    
    # Clean up response
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
    response_text = response_text.strip()
    
    try:
        note_data = json.loads(response_text)
    except json.JSONDecodeError:
        note_data = {
            "client_name": "Not specified",
            "session_date": "Not specified",
            "session_length": "Not specified",
            "subjective": response_text,
            "objective": "Unable to parse structured response",
            "assessment": "Please review transcript manually",
            "plan": "Regenerate note or enter manually",
            "clinical_tone": "Unknown"
        }
    
    soap_note = SOAPNote(**note_data)
    soap_note = validate_soap_note(soap_note)
    
    return soap_note


def validate_soap_note(note: SOAPNote) -> SOAPNote:
    """Validate a SOAP note for completeness."""
    validation_notes = []
    
    if note.client_name == "Not specified" or not note.client_name:
        validation_notes.append("⚠️ Client name is missing")
    
    if note.session_length == "Not specified" or not note.session_length:
        validation_notes.append("⚠️ Session length is missing")
    
    if len(note.subjective) < 20:
        validation_notes.append("⚠️ Subjective section may be incomplete")
    
    if len(note.objective) < 20:
        validation_notes.append("⚠️ Objective section may be incomplete")
    
    if len(note.assessment) < 20:
        validation_notes.append("⚠️ Assessment section may be incomplete")
    
    if len(note.plan) < 20:
        validation_notes.append("⚠️ Plan section may be incomplete")
    
    note.validation_notes = validation_notes
    note.is_complete = len(validation_notes) == 0
    
    return note


# ============================================================
# STREAMLIT UI
# ============================================================

st.set_page_config(
    page_title="Moonlight AI Note Builder",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #1E3A5F;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: #1E3A5F;
        margin-bottom: 0.5rem;
    }
    .main-header p {
        color: #666;
        font-size: 1.1rem;
    }
    .status-complete {
        background-color: #d4edda;
        border: 1px solid #28a745;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .status-warning {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .soap-section {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .hipaa-badge {
        background-color: #1E3A5F;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-size: 0.8rem;
        float: right;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🌙 Moonlight AI Note Builder</h1>
    <p>Clinical Documentation Assistant</p>
    <span class="hipaa-badge">HIPAA Considerations Applied</span>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'transcript' not in st.session_state:
    st.session_state.transcript = None
if 'soap_note' not in st.session_state:
    st.session_state.soap_note = None
if 'step' not in st.session_state:
    st.session_state.step = 1

# Progress indicator
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("**1️⃣ Input**" if st.session_state.step >= 1 else "1️⃣ Input")
with col2:
    st.markdown("**2️⃣ Transcript**" if st.session_state.step >= 2 else "2️⃣ Transcript")
with col3:
    st.markdown("**3️⃣ Generate**" if st.session_state.step >= 3 else "3️⃣ Generate")
with col4:
    st.markdown("**4️⃣ Validate**" if st.session_state.step >= 4 else "4️⃣ Validate")
st.markdown("---")

# Step 1: Input
st.subheader("📤 Step 1: Input Session Content")

input_mode = st.radio(
    "Choose input method:",
    ["🎙️ Record Audio", "📁 Upload Audio File", "📝 Enter Transcript Directly"],
    horizontal=True,
)

uploaded_file = None
audio_bytes = None

if input_mode == "🎙️ Record Audio":
    st.info("🎙️ Click the microphone to start recording your session notes")
    audio_value = st.audio_input("Record your session summary")
    
    if audio_value:
        st.audio(audio_value)
        if st.button("🎯 Transcribe Recording", type="primary", use_container_width=True):
            with st.spinner("Transcribing audio with Deepgram Nova-2..."):
                try:
                    audio_bytes = audio_value.read()
                    result = transcribe_audio_sync(audio_bytes, "audio/wav")
                    st.session_state.transcript = result['transcript']
                    st.session_state.confidence = result.get('confidence', 0)
                    st.session_state.step = 2
                    st.success(f"✅ Transcription complete! Confidence: {st.session_state.confidence:.1%}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Transcription error: {str(e)}")

elif input_mode == "📁 Upload Audio File":
    uploaded_file = st.file_uploader(
        "Upload an audio recording of the therapy session",
        type=['wav', 'mp3', 'm4a', 'mp4', 'ogg', 'webm', 'aac'],
    )
elif input_mode == "📝 Enter Transcript Directly":
    direct_transcript = st.text_area(
        "Paste or type session transcript:",
        height=200,
        placeholder="Enter the session transcript here..."
    )
    if direct_transcript and st.button("✅ Use This Transcript", type="primary"):
        st.session_state.transcript = direct_transcript
        st.session_state.confidence = 1.0
        st.session_state.step = 2
        st.success("✅ Transcript loaded!")
        st.rerun()

# Optional context
with st.expander("➕ Add Session Context (Optional)", expanded=False):
    context_client_name = st.text_input("Client Name", placeholder="e.g., John D.")
    context_date = st.date_input("Session Date", value=datetime.now())
    context_length = st.selectbox(
        "Session Length",
        ["30 minutes", "45 minutes", "50 minutes", "60 minutes", "90 minutes"],
        index=2
    )

# Audio transcription
if uploaded_file is not None:
    st.audio(uploaded_file, format=uploaded_file.type)
    
    if st.button("🎯 Transcribe Audio", type="primary", use_container_width=True):
        with st.spinner("Transcribing audio with Deepgram Nova-2..."):
            try:
                audio_bytes = uploaded_file.read()
                result = transcribe_audio_sync(audio_bytes, uploaded_file.type)
                st.session_state.transcript = result['transcript']
                st.session_state.confidence = result.get('confidence', 0)
                st.session_state.step = 2
                st.success(f"✅ Transcription complete! Confidence: {st.session_state.confidence:.1%}")
            except Exception as e:
                st.error(f"Transcription error: {str(e)}")

# Step 2: Review Transcript
if st.session_state.transcript:
    st.markdown("---")
    st.subheader("📝 Step 2: Review Transcript")
    
    edited_transcript = st.text_area(
        "Edit transcript if needed:",
        value=st.session_state.transcript,
        height=200,
    )
    
    context_parts = []
    if context_client_name:
        context_parts.append(f"Client Name: {context_client_name}")
    if context_date:
        context_parts.append(f"Session Date: {context_date.strftime('%Y-%m-%d')}")
    if context_length:
        context_parts.append(f"Session Length: {context_length}")
    additional_context = ". ".join(context_parts)
    
    if st.button("🧠 Generate SOAP Note", type="primary", use_container_width=True):
        with st.spinner("Generating clinical documentation..."):
            try:
                soap_note = generate_soap_note(edited_transcript, additional_context)
                st.session_state.soap_note = soap_note
                st.session_state.step = 4
                st.success("✅ SOAP note generated!")
            except Exception as e:
                st.error(f"Error generating note: {str(e)}")

# Step 4: Display SOAP Note
if st.session_state.soap_note:
    st.markdown("---")
    st.subheader("📋 Step 4: Review & Validate")
    
    note = st.session_state.soap_note
    
    if note.is_complete:
        st.markdown('<div class="status-complete">✅ <strong>Note is complete and validated</strong></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-warning">⚠️ <strong>Validation warnings detected</strong></div>', unsafe_allow_html=True)
        for v_note in note.validation_notes:
            st.warning(v_note)
    
    st.markdown("### Clinical Documentation")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Client", note.client_name)
    with col2:
        st.metric("Date", note.session_date)
    with col3:
        st.metric("Duration", note.session_length)
    
    st.markdown(f"**Clinical Tone:** {note.clinical_tone}")
    st.markdown("---")
    
    st.markdown("#### Subjective")
    st.markdown(f'<div class="soap-section">{note.subjective}</div>', unsafe_allow_html=True)
    
    st.markdown("#### Objective")
    st.markdown(f'<div class="soap-section">{note.objective}</div>', unsafe_allow_html=True)
    
    st.markdown("#### Assessment")
    st.markdown(f'<div class="soap-section">{note.assessment}</div>', unsafe_allow_html=True)
    
    st.markdown("#### Plan")
    st.markdown(f'<div class="soap-section">{note.plan}</div>', unsafe_allow_html=True)
    
    # Export
    st.markdown("---")
    st.subheader("📤 Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        export_text = f"""SOAP NOTE
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Client: {note.client_name}
Date: {note.session_date}
Session Length: {note.session_length}
Clinical Tone: {note.clinical_tone}

SUBJECTIVE:
{note.subjective}

OBJECTIVE:
{note.objective}

ASSESSMENT:
{note.assessment}

PLAN:
{note.plan}

---
Validation Status: {"Complete" if note.is_complete else "Warnings Present"}
"""
        st.download_button(
            "📄 Download as Text",
            data=export_text,
            file_name=f"soap_note_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col2:
        export_json = json.dumps(note.model_dump(), indent=2)
        st.download_button(
            "🔗 Download as JSON (EMR)",
            data=export_json,
            file_name=f"soap_note_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    st.info("💡 **Lightning Step Integration:** JSON export format designed for EMR integration.")

# Reset
st.markdown("---")
if st.button("🔄 Start New Note", use_container_width=True):
    st.session_state.transcript = None
    st.session_state.soap_note = None
    st.session_state.step = 1
    st.rerun()

st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem; margin-top: 2rem;">
    <p>🌙 Moonlight AI Note Builder | Built for Moonlight Mountain Recovery</p>
</div>
""", unsafe_allow_html=True)
