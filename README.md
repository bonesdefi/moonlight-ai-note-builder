# 🌙 Moonlight AI Note Builder

Clinical documentation assistant that transforms therapy session recordings into structured SOAP notes.

**Built for Moonlight Mountain Recovery**

🚀 **[Live Demo: https://moonlight-ai.streamlit.app/](https://moonlight-ai.streamlit.app/)**

## Features

- **Audio Transcription**: Upload session recordings for automatic transcription using Deepgram Nova-2
- **AI-Powered SOAP Notes**: Generate professional clinical documentation using Claude
- **Smart Validation**: Automatic checking for required fields (client name, session length, all SOAP sections)
- **Export Ready**: Download as text or JSON format for EMR integration

## Quick Start

### 1. Install Dependencies

```bash
cd moonlight-note-builder
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.streamlit/secrets.toml` file with your API keys:

```bash
mkdir -p .streamlit
cat > .streamlit/secrets.toml << EOF
DEEPGRAM_API_KEY = "your_deepgram_key_here"
ANTHROPIC_API_KEY = "your_anthropic_key_here"
EOF
```

Get your keys from:
- Deepgram: https://console.deepgram.com/
- Anthropic: https://console.anthropic.com/

> **Note:** Using Streamlit secrets (`.streamlit/secrets.toml`) instead of `.env` files resolves transcription issues with uploaded audio files and works seamlessly on Streamlit Cloud.

### 3. Run the App

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Workflow

1. **Upload Audio** or **Enter Transcript Directly**
2. **Review Transcript** - Edit if needed, add session context
3. **Generate Note** - AI creates a structured SOAP note
4. **Validate & Export** - Review validation, download for EMR

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| Transcription | Deepgram Nova-2 |
| Note Generation | Claude 4.5 Haiku |
| Validation | Pydantic |

## HIPAA Considerations

For production deployment:

- Data encryption at rest and in transit (TLS 1.3)
- Business Associate Agreements (BAA) with Deepgram and Anthropic
- No PHI logging - audio and transcripts not persisted
- Role-based access control
- Audit logging for compliance

## Lightning Step Integration

The JSON export format is designed for EMR integration:

```json
{
  "client_name": "John D.",
  "session_date": "2024-01-15",
  "session_length": "50 minutes",
  "subjective": "...",
  "objective": "...",
  "assessment": "...",
  "plan": "...",
  "clinical_tone": "...",
  "is_complete": true
}
```

## Author

Michael - Built with passion for the recovery community 🙏
