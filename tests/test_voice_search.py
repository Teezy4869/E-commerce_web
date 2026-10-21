"""
Tests for Voice Search (VS-01, VS-02, VS-03)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.product_repository import ProductRepository
from application.query_service import QueryService
from application.search_service import SearchService
from application.speech_service import SpeechService
from application.ranking_service import RankingService
from presentation.voice_input import VoiceInput


def setup():
    repo = ProductRepository()
    search = SearchService(repo)
    query = QueryService()
    speech = SpeechService()
    ranking = RankingService()
    return repo, search, query, speech, ranking


def test_vs01_simulated_transcription():
    """VS-01: SpeechService returns the same text (simulated STT)."""
    _, _, _, speech, _ = setup()
    audio_input = "find black running shoes"
    text = speech.transcribe(audio_input)
    assert text == audio_input, \
        f"Expected '{audio_input}', got '{text}'"
    print("  PASS: VS-01 simulated transcription")


def test_vs02_voice_query_representation():
    """VS-02: QueryService produces correct voice query representation."""
    _, _, query, speech, _ = setup()
    audio = "find running shoes"
    transcribed = speech.transcribe(audio)
    q = query.voice_query(transcribed)

    assert q["type"] == "voice", f"Expected type 'voice', got '{q['type']}'"
    assert q["query"] == "find running shoes", \
        f"Expected query 'find running shoes', got '{q['query']}'"
    print("  PASS: VS-02 voice query representation")


def test_vs03_voice_retrieval():
    """VS-03: Full voice pipeline: audio → transcription → query → retrieval → ranking."""
    _, search, query, speech, ranking = setup()

    # Step 1: Simulated transcription
    audio = "find running shoes"
    transcribed = speech.transcribe(audio)

    # Step 2: Create query representation
    q = query.voice_query(transcribed)

    # Step 3: Retrieve candidates
    candidates = search.search(q)
    assert len(candidates) > 0, "Expected results for voice query"

    # Step 4: Rank results
    ranked = ranking.rank(candidates)
    assert len(ranked) > 0, "Expected ranked results"
    assert ranked[0]["score"] >= ranked[-1]["score"], \
        "Results should be ranked by descending score"

    # Verify running-shoe products appear
    product_names = [r["product"]["name"] for r in ranked]
    has_running = any("Running" in name for name in product_names)
    assert has_running, \
        f"Expected a running-shoe product, got {product_names}"
    print("  PASS: VS-03 voice retrieval pipeline")


def test_vs04_voice_input_component():
    """VoiceInput delegates simulated capture to SpeechService."""
    _, _, _, speech, _ = setup()
    voice_input = VoiceInput(speech)
    assert voice_input.capture("find black shoes") == "find black shoes"
    try:
        voice_input.capture("   ")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for empty voice input")
    print("  PASS: VS-04 VoiceInput component integration")


if __name__ == "__main__":
    print("\n=== VOICE SEARCH TESTS ===\n")
    test_vs01_simulated_transcription()
    test_vs02_voice_query_representation()
    test_vs03_voice_retrieval()
    test_vs04_voice_input_component()
    print("\n  All voice search tests passed!\n")
