class SpeechService:
    """
    Application Layer — SpeechService

    Validate a browser-recognized or manually entered transcript. This
    backend does not perform audio recognition or call a speech API.
    """

    def transcribe(self, audio_input):
        """Return the supplied transcript while validating the input."""
        if not isinstance(audio_input, str) or not audio_input.strip():
            raise ValueError("voice transcript must contain non-empty text")
        return audio_input.strip()
