# Voice Integration (STT & TTS) Implementation Plan

We will add Speech-to-Text (STT) for voice input and Text-to-Speech (TTS) for voice output to make the application more accessible and interactive.

## User Review Required

> [!IMPORTANT]
> **Edge TTS Voice Selection**: I plan to use the `ar-EG-SalmaNeural` voice from Microsoft Edge TTS by default. This is a very natural-sounding Egyptian female voice. If you prefer a male voice, we can use `ar-EG-ShakirNeural`.

## Proposed Changes

### Backend

#### [MODIFY] [requirements.txt](file:///e:/salah/salah_programing/clinical-decision-support-ref/requirements.txt)
- Add `edge-tts` for high-quality Arabic Text-to-Speech.
- Add `python-multipart` to support file uploads in FastAPI (needed to receive voice recordings).

#### [MODIFY] [backend/main.py](file:///e:/salah/salah_programing/clinical-decision-support-ref/backend/main.py)
- **New Endpoint: `POST /api/transcribe`**:
  - Will receive an audio file upload from the frontend.
  - Will use the Groq client to call the `whisper-large-v3-turbo` model for lightning-fast Arabic speech recognition.
  - Returns the transcribed text.
- **New Endpoint: `POST /api/tts`**:
  - Will receive text from the frontend.
  - Will use `edge-tts` to generate speech in real-time.
  - Will stream the generated MP3 audio back to the frontend.

### Frontend

#### [MODIFY] [frontend/src/components/ChatInterface.jsx](file:///e:/salah/salah_programing/clinical-decision-support-ref/frontend/src/components/ChatInterface.jsx)
- Import `Mic` and `Square` icons from `lucide-react`.
- Add a new "Microphone" button next to the text input field.
- Implement the `MediaRecorder` API to capture audio from the user's microphone when they hold or click the button.
- Send the recorded audio Blob to `/api/transcribe`.
- Automatically populate the text input or send the transcribed message directly.

#### [MODIFY] [frontend/src/components/MessageBubble.jsx](file:///e:/salah/salah_programing/clinical-decision-support-ref/frontend/src/components/MessageBubble.jsx)
- Import the `Volume2` icon from `lucide-react`.
- Add a small "Play Audio" button to AI message bubbles.
- When clicked, call `/api/tts` with the message text and play the audio stream using an HTML5 `<audio>` element.

## Verification Plan

### Manual Verification
1. I will install the new Python dependencies.
2. I will ask you to open the React app in your browser, click the Microphone icon, grant permission, and speak a test phrase in Arabic.
3. We will verify that the text is correctly transcribed by Groq and sent to the LLM.
4. We will click the Speaker icon on the AI's response and verify that the Edge TTS plays the audio clearly.
