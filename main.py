"""Assignment 06 — Multimodal E-Commerce Search demonstration."""

from application.image_service import ImageService
from application.query_service import QueryService
from application.ranking_service import RankingService
from application.search_service import SearchService
from application.speech_service import SpeechService
from data.order_repository import OrderRepository
from data.product_repository import ProductRepository
from data.vector_index import VectorIndex
from presentation.image_upload import ImageUpload
from presentation.search_result_view import SearchResultView
from presentation.search_ui import SearchUI
from presentation.voice_input import VoiceInput


def build_system():
    """Build the approved three-layer prototype and return its UI entry point."""
    product_repository = ProductRepository()
    order_repository = OrderRepository()
    vector_index = VectorIndex(product_repository)

    query_service = QueryService()
    speech_service = SpeechService()
    image_service = ImageService()
    search_service = SearchService(product_repository, vector_index, order_repository)
    ranking_service = RankingService()

    voice_input = VoiceInput(speech_service)
    image_upload = ImageUpload(image_service)

    search_ui = SearchUI(
        query_service=query_service,
        search_service=search_service,
        ranking_service=ranking_service,
        voice_input=voice_input,
        image_upload=image_upload,
    )

    result_view = SearchResultView()
    return search_ui, result_view, product_repository, order_repository


def main():
    search_ui, result_view, product_repository, order_repository = build_system()

    print("=" * 60)
    print("  E-COMMERCE MULTIMODAL SEARCH SYSTEM")
    print("  Assignment 06 — Demonstration")
    print("=" * 60)

    print("\n" + "#" * 60)
    print('  DEMO 1: TEXT SEARCH')
    print('  Query: "black shoes"')
    print("#" * 60)
    ranked_results = search_ui.text_search("black shoes")
    result_view.display_ranked_results(ranked_results, 'Text Search: "black shoes"')

    print("\n" + "#" * 60)
    print("  DEMO 2: VOICE SEARCH (Simulated)")
    print('  Audio input: "find running shoes"')
    print("#" * 60)
    ranked_results = search_ui.voice_search("find running shoes")
    result_view.display_ranked_results(
        ranked_results,
        'Voice Search: "find running shoes"',
    )

    print("\n" + "#" * 60)
    print("  DEMO 3: IMAGE SEARCH")
    print("  Query image: images/query_shoes.jpg")
    print("#" * 60)
    ranked_results = search_ui.image_search("images/query_shoes.jpg")
    result_view.display_ranked_results(ranked_results, "Image Search: shoe-like image")

    print("\n" + "#" * 60)
    print("  DEMO 4: ORDER SEARCH")
    print('  Order ID: "O001"')
    print("#" * 60)
    order = search_ui.order_search("O001")
    result_view.display_order(order)

    print("\n" + "=" * 60)
    print("  DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("  Architecture: Presentation -> Application -> Data")
    print("  Search modes demonstrated: Text, Voice, Image")
    print("  Products in dataset:", len(product_repository.all_products()))
    print("  Orders in dataset:", len(order_repository.all_orders()))
    print("=" * 60)


if __name__ == "__main__":
    main()
