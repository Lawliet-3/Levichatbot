import streamlit as st
from audio_recorder_streamlit import audio_recorder
import base64
import json
import requests

class VoiceRecorder:
    def __init__(self):
        self.audio_bytes = None

    def record_audio(self):
        st.write("Record your feedback (optional)")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Audio recorder component
            audio_bytes = audio_recorder(
                text="Click to record",
                recording_color="#e31837",
                neutral_color="#6c757d",
                icon_name="mic",
                icon_size="2x"
            )

        with col2:
            if st.button("Clear Recording"):
                self.audio_bytes = None
                st.rerun()

        if audio_bytes:
            self.audio_bytes = audio_bytes
            st.audio(audio_bytes, format="audio/wav")
            
            # Convert to base64 for storage/transmission
            encoded_audio = base64.b64encode(audio_bytes).decode()
            return encoded_audio
        
        return None

    def submit_voice_feedback(self, survey_id: str, audio_data: str):
        try:
            response = requests.post(
                "http://localhost:8000/survey/voice-feedback",
                json={
                    "survey_id": survey_id,
                    "audio_data": audio_data
                },
                timeout=10
            )
            
            if response.status_code == 200:
                st.success("Voice feedback submitted successfully!")
            else:
                st.error("Failed to submit voice feedback")
                
        except requests.exceptions.RequestException as e:
            st.error(f"Error submitting voice feedback: {str(e)}")