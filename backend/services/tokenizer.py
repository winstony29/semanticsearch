"""
Sentence tokenization using spaCy.

Splits text into sentences while handling edge cases like abbreviations.
Falls back to simple splitting if spaCy is not available.
"""

try:
    import spacy
    # Load spaCy model (must run: python -m spacy download en_core_web_sm)
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except (ImportError, OSError):
    SPACY_AVAILABLE = False
    print("Warning: spaCy not available. Using fallback sentence splitter.")


def tokenize_text(text: str) -> list[str]:
    """
    Split text into sentences.

    Args:
        text: Input text to tokenize

    Returns:
        List of sentence strings, whitespace stripped, empty strings removed
    """
    if not text or not text.strip():
        return []

    if SPACY_AVAILABLE:
        return _tokenize_with_spacy(text)
    else:
        return _tokenize_fallback(text)


def _tokenize_with_spacy(text: str) -> list[str]:
    """Tokenize using spaCy (recommended)."""
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents]
    return [s for s in sentences if s]  # Filter out empty strings


def _tokenize_fallback(text: str) -> list[str]:
    """
    Simple fallback tokenizer if spaCy is not available.
    Splits on ". " which is crude but works for basic cases.
    """
    # Simple split on period + space
    sentences = text.split(". ")

    # Clean up
    result = []
    for i, sent in enumerate(sentences):
        sent = sent.strip()
        if sent:
            # Add period back except for the last sentence
            if i < len(sentences) - 1 and not sent.endswith("."):
                sent += "."
            result.append(sent)

    return result


# Test function for development
if __name__ == "__main__":
    test_text = """Hi I am Nickolas and I am participating in a hackathon. I am doing this with my 3 other friends. I can not wait to start building and win first prize."""

    sentences = tokenize_text(test_text)
    print(f"Tokenized {len(sentences)} sentences:")
    for i, sent in enumerate(sentences, 1):
        print(f"{i}. {sent}")
