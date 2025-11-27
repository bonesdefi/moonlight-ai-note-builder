# Architecture Summary: Moonlight AI Note Builder

## System Overview
The Moonlight AI Note Builder is a lightweight, HIPAA-aware prototype designed to streamline clinical documentation. It transforms unstructured therapy session audio into structured, EMR-ready SOAP notes using a state-of-the-art AI pipeline.

## Technology Stack & Rationale
*   **Frontend: Streamlit**
    *   *Why:* Rapid prototyping, native Python integration, and built-in support for audio handling. Allows for a functional, interactive UI without the overhead of a complex React/Vue setup.
*   **Transcription: Deepgram Nova-2**
    *   *Why:* Industry-leading speed and accuracy for medical terminology. The `nova-2` model offers superior diarization (speaker separation) and smart formatting compared to standard Whisper implementations.
*   **Intelligence: Anthropic Claude 3.5 Sonnet**
    *   *Why:* Superior reasoning capabilities for clinical context compared to GPT-4o. Claude excels at maintaining clinical tone, following complex formatting instructions, and reducing hallucinations in medical summaries.
*   **Validation: Pydantic**
    *   *Why:* Robust data validation ensures that generated notes meet strict schema requirements before they can be exported, preventing incomplete data entry.

## HIPAA Compliance Strategy
For a production deployment, the following measures would be implemented:
1.  **BAA Coverage:** Execute Business Associate Agreements (BAA) with both Deepgram and Anthropic.
2.  **Zero Persistence:** The current prototype processes data in-memory. In production, audio files would be processed ephemerally and immediately deleted after transcription.
3.  **Encryption:** End-to-end encryption (TLS 1.3) for data in transit. At-rest encryption for any temporary storage using AWS KMS or equivalent.
4.  **Access Control:** Strict IAM roles and audit logging to track who accessed which note generation event.

## Scalability
To handle high daily volume (e.g., hundreds of clinicians):
*   **Async Processing:** Decouple the UI from processing using a message queue (e.g., Celery/Redis). The user uploads audio, and the job is processed in the background, notifying them when complete.
*   **Stateless Architecture:** The application logic is stateless, allowing for horizontal scaling of the application servers behind a load balancer.
*   **Batching:** Deepgram and Anthropic APIs support high concurrency, allowing for parallel processing of multiple sessions.

## Lightning Step Integration
The application is designed as a "pre-processor" for Lightning Step (EMR):
*   **JSON Schema:** The output format is strictly typed JSON, matching potential EMR API endpoints.
*   **Direct Push:** In a future iteration, the "Download JSON" button would be replaced with a "Sync to Lightning Step" button, using the EMR's API to POST the structured data directly to the patient's record.

## Key Design Choices
*   **"Human-in-the-Loop" Workflow:** We intentionally included a "Review Transcript" step. AI is a tool, not a replacement; clinicians must verify the transcript accuracy before note generation to ensure clinical integrity.
*   **Strict Validation:** The application refuses to mark a note as "Complete" unless critical fields (Client Name, Session Length) are present, enforcing documentation standards automatically.
