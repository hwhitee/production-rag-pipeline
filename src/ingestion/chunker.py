from src.core.config import settings


def chunk_text(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = settings.chunk_size - settings.chunk_overlap
    return [
        " ".join(words[start : start + settings.chunk_size]) for start in range(0, len(words), step)
    ]
