"""
Sentence tokenization using wtpsplit.

Splits text into sentences across all languages using the SaT model.
Falls back to regex splitting if wtpsplit is not available.
"""

import re
from dataclasses import dataclass

# Initialize wtpsplit model once at module level
try:
    from wtpsplit import SaT
    sat = SaT("sat-3l")
    WTPSPLIT_AVAILABLE = True
except (ImportError, Exception) as e:
    WTPSPLIT_AVAILABLE = False
    print(f"Warning: wtpsplit not available ({e}). Using fallback sentence splitter.")


# Lazy-loaded spaCy models
_spacy_models = {}

# Clause splitting thresholds
CLAUSE_SPLIT_WORD_THRESHOLD = 15
CLAUSE_SPLIT_CHAR_THRESHOLD = 30  # for CJK languages


@dataclass
class TokenizedResult:
    clauses: list[str]              # all clauses (flat list)
    clause_to_sentence: list[int]   # index mapping: clause i belongs to sentence clause_to_sentence[i]
    sentences: list[str]            # original sentences before clause splitting


def _detect_language(text: str) -> str:
    """
    Detect language using Unicode code points.
    Crude detection for demo languages only.
    """
    for char in text:
        cp = ord(char)
        if 0x4E00 <= cp <= 0x9FFF: return "zh"
        if 0x3040 <= cp <= 0x30FF: return "ja"
        if 0xAC00 <= cp <= 0xD7AF: return "ko"
    return "en"


def _get_spacy_model(lang: str):
    """
    Lazy-load spaCy model for given language.
    Returns None if model is not available.
    """
    if lang not in _spacy_models:
        model_map = {
            "en": "en_core_web_sm",
            "zh": "zh_core_web_sm",
            "ja": "ja_core_web_sm",
            "ko": "ko_core_news_sm",
            "de": "de_core_news_sm",
            "fr": "fr_core_news_sm",
        }
        model_name = model_map.get(lang)
        if model_name is None:
            return None
        try:
            import spacy
            _spacy_models[lang] = spacy.load(model_name)
        except OSError:
            return None
    return _spacy_models[lang]


def _should_clause_split(sentence: str, lang: str) -> bool:
    """
    Determine if a sentence should be split into clauses.
    """
    if lang in ("zh", "ja", "ko"):
        return len(sentence) > CLAUSE_SPLIT_CHAR_THRESHOLD
    return len(sentence.split()) > CLAUSE_SPLIT_WORD_THRESHOLD


def _split_clauses(sentence: str, nlp) -> list[str]:
    """
    Split a sentence into clauses using spaCy dependency parsing.
    """
    doc = nlp(sentence)
    clause_boundaries = []
    for token in doc:
        if token.dep_ in ("advcl", "relcl", "ccomp", "xcomp", "acl"):
            clause_boundaries.append(token.left_edge.i)
    if not clause_boundaries:
        return [sentence]
    boundaries = sorted(set([0] + clause_boundaries + [len(doc)]))
    clauses = []
    for i in range(len(boundaries) - 1):
        clause = doc[boundaries[i]:boundaries[i+1]].text.strip()
        if clause:
            clauses.append(clause)
    return clauses if clauses else [sentence]


def tokenize_text(text: str) -> TokenizedResult:
    """
    Split text into sentences and then into clauses.

    Args:
        text: Input text to tokenize

    Returns:
        TokenizedResult with clauses, clause_to_sentence mapping, and original sentences
    """
    # Strip whitespace from input
    text = text.strip()

    # If empty string, return empty result
    if not text:
        return TokenizedResult(clauses=[], clause_to_sentence=[], sentences=[])

    # Stage 1: sentence splitting with wtpsplit
    if WTPSPLIT_AVAILABLE:
        try:
            sentences = sat.split(text)
        except Exception as e:
            print(f"Warning: wtpsplit failed ({e}). Using fallback.")
            sentences = re.split(r'(?<=[.!?。!?])\s+', text)
    else:
        sentences = re.split(r'(?<=[.!?。!?])\s+', text)

    sentences = [s.strip() for s in sentences if s.strip()]

    # Stage 2: clause sub-splitting
    lang = _detect_language(text)
    nlp = _get_spacy_model(lang)

    clauses = []
    clause_to_sentence = []

    for sent_idx, sentence in enumerate(sentences):
        if nlp is not None and _should_clause_split(sentence, lang):
            sub_clauses = _split_clauses(sentence, nlp)
            for clause in sub_clauses:
                clauses.append(clause)
                clause_to_sentence.append(sent_idx)
        else:
            clauses.append(sentence)
            clause_to_sentence.append(sent_idx)

    return TokenizedResult(
        clauses=clauses,
        clause_to_sentence=clause_to_sentence,
        sentences=sentences,
    )


# Test function for development
if __name__ == "__main__":
    tests = [
        "Although it was raining, we went to the beach because we had planned it for weeks. The sun came out later.",
        "The dog ran fast.",
        "虽然今天下雨了，我们还是去了海滩，因为我们已经计划了好几个星期。太阳后来出来了。",
        "We should consider expanding to Japan. Our revenue grew 10% last quarter.",
    ]
    for t in tests:
        result = tokenize_text(t)
        lang = _detect_language(t)
        print(f"[{lang}] Input: {t}")
        print(f"  Sentences ({len(result.sentences)}): {result.sentences}")
        print(f"  Clauses ({len(result.clauses)}): {result.clauses}")
        print(f"  Mapping: {result.clause_to_sentence}")
        print()
