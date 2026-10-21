class QueryService:
    """
    Application Layer — QueryService

    Converts text, voice, and image inputs into a common query
    representation used by SearchService.
    """

    @staticmethod
    def _validate_text(text, field_name):
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{field_name} must be a non-empty string")
        return text.strip()

    def text_query(self, text, filters=None):
        """Create a common query representation for text input."""
        return {
            "type": "text",
            "query": self._validate_text(text, "text"),
            "filters": filters or {}
        }

    def voice_query(self, text, filters=None):
        """Create a common query representation for transcribed voice input."""
        return {
            "type": "voice",
            "query": self._validate_text(text, "voice text"),
            "filters": filters or {}
        }

    def image_query(self, embedding, filters=None):
        """Create a common query representation for an image embedding."""
        if not hasattr(embedding, "__len__") or len(embedding) == 0:
            raise ValueError("image embedding must be a non-empty sequence")
        return {
            "type": "image",
            "embedding": list(embedding),
            "filters": filters or {}
        }
