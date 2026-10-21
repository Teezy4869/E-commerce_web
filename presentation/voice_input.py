class VoiceInput:
    """
    Presentation Layer — VoiceInput

    Receives a browser-recognized or manually edited transcript and delegates
    validation to SpeechService. No audio bytes are sent to this component.
    """

    def __init__(self, speech_service):
        self.speech_service = speech_service

    def capture(self, audio_input):
        if not isinstance(audio_input, str) or not audio_input.strip():
            raise ValueError("voice input must be non-empty text in the baseline")
        transcribed = self.speech_service.transcribe(audio_input)
        return transcribed
