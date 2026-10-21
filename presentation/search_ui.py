class SearchUI:
    """
    Presentation Layer — SearchUI

    Coordinates user interaction with application services. It never
    accesses repositories or databases directly.
    """

    def __init__(
        self,
        query_service,
        search_service,
        ranking_service,
        voice_input,
        image_upload,
    ):
        self.query_service = query_service
        self.search_service = search_service
        self.ranking_service = ranking_service
        self.voice_input = voice_input
        self.image_upload = image_upload

    def _rank(self, query):
        candidates = self.search_service.search(query)
        print(f"  [SearchUI] Retrieved {len(candidates)} candidates")
        ranked = self.ranking_service.rank(candidates)
        print("  [SearchUI] Ranking complete")
        return ranked

    def text_search(self, text):
        print(f'\n  [SearchUI] Text search input: "{text}"')
        query = self.query_service.text_query(text)
        print(f"  [SearchUI] Query representation: {query}")
        return self._rank(query)

    def voice_search(self, audio_input):
        print(f'\n  [SearchUI] Voice search input: "{audio_input}"')
        transcribed = self.voice_input.capture(audio_input)
        query = self.query_service.voice_query(transcribed)
        print(f"  [SearchUI] Query representation: {query}")
        return self._rank(query)

    def image_search(self, image_input):
        print(f"\n  [SearchUI] Image search input: {image_input}")
        embedding = self.image_upload.upload(image_input)
        query = self.query_service.image_query(embedding)
        print(f"  [SearchUI] Query representation: type={query['type']}")
        return self._rank(query)

    def order_search(self, order_id):
        print(f'\n  [SearchUI] Order search: "{order_id}"')
        return self.search_service.search_order(order_id)
