from src.ingestion.chunker import chunk_text


def test_empty_text_has_no_chunks() -> None:
    assert chunk_text(" \n ") == []


def test_chunks_overlap_and_preserve_all_tokens(monkeypatch) -> None:
    from src.core.config import settings

    monkeypatch.setattr(settings, "chunk_size", 10)
    monkeypatch.setattr(settings, "chunk_overlap", 2)
    words = [f"word{i}" for i in range(25)]
    result = chunk_text(" ".join(words))
    assert result[0].split()[-2:] == result[1].split()[:2]
    flattened = set(" ".join(result).split())
    assert flattened == set(words)
