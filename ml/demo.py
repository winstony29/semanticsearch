"""Runnable demo for the ML slice.

Usage:
    python -m ml.demo                   # Real OpenAI calls. Needs OPENAI_API_KEY.
    python -m ml.demo --mock            # Deterministic mocks. No keys needed.
    python -m ml.demo --before "..." --after "..."   # Pass your own text.

The mock mode hand-builds embeddings such that the four pairs in
``ml._mock_align`` classify as: unchanged (paraphrase), modified, unchanged
(verbatim), and a low-similarity pair that gets split into removed+added.
Useful for confirming the pipeline shape without burning credits.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Make sibling packages importable when run as a script (not via -m).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np

# Best-effort: force UTF-8 on stdout (Windows cmd defaults to cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # pragma: no cover — older Pythons
    pass

import ml.pipeline as pipeline_mod
from backend.models.schemas import ConceptDiff, DiffResponse
from ml._mock_align import SAMPLE_AFTER, SAMPLE_BEFORE


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def _near(v: np.ndarray, eps: float, rng: np.random.Generator) -> np.ndarray:
    perp = _unit(rng.standard_normal(v.shape).astype("float32"))
    perp = _unit(perp - perp.dot(v) * v)
    return _unit(np.sqrt(max(0.0, 1.0 - eps * eps)) * v + eps * perp)


def _build_mock_embeddings() -> dict[str, np.ndarray]:
    """Hand-built embeddings shaped to produce realistic similarity ranges
    against the canned _mock_align output."""
    rng = np.random.default_rng(7)
    base = _unit(rng.standard_normal(1536).astype("float32"))
    emb: dict[str, np.ndarray] = {
        "b0": base,
        "a0": _near(base, 0.24, rng),  # ~0.97 — unchanged
        "b1": _unit(rng.standard_normal(1536).astype("float32")),
        "b2": _unit(rng.standard_normal(1536).astype("float32")),
        "b3": _unit(rng.standard_normal(1536).astype("float32")),
        "b4": _unit(rng.standard_normal(1536).astype("float32")),
    }
    emb["a1"] = _near(emb["b1"], 0.62, rng)  # ~0.78 — modified
    emb["a2"] = emb["b2"].copy()             # 1.00 — unchanged (verbatim)
    emb["a3"] = _near(emb["b3"], 0.95, rng)  # ~0.31 — split
    emb["a4"] = _unit(rng.standard_normal(1536).astype("float32"))
    return emb


def _install_mocks() -> None:
    """Monkey-patch the orchestrator's embed_clauses + extract_concepts."""
    embeddings = _build_mock_embeddings()

    async def fake_embed(_alignment):
        return embeddings

    async def fake_concepts(_before, _after):
        return ConceptDiff(
            summary="(mock) Termination broadened; payment terms removed; liability cap added.",
            concepts=[],
        ), "ok"

    pipeline_mod.embed_clauses = fake_embed
    pipeline_mod.extract_concepts = fake_concepts


# ---------- Pretty-printing -------------------------------------------------

_RESET = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_BLUE = "\033[34m"
_GREY = "\033[90m"


_COLOR_BY_CLASS = {
    "unchanged": _GREEN,
    "modified": _YELLOW,
    "removed": _RED,
    "added": _BLUE,
}


def _supports_color() -> bool:
    # Disable colour on Windows cmd unless ANSI is enabled.
    return sys.stdout.isatty() and (os.name != "nt" or os.environ.get("WT_SESSION"))


def _c(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}" if _supports_color() else text


def _print_section(title: str) -> None:
    print()
    print(_c(f"-- {title} ".ljust(78, "-"), _BOLD))


def _print_clauses(label: str, clauses, max_text: int = 70) -> None:
    print(_c(label, _BOLD))
    if not clauses:
        print(_c("  (none)", _DIM))
        return
    for c in clauses:
        col = _COLOR_BY_CLASS.get(c.classification, _RESET)
        partner = c.paired_with or "----"
        text = c.text[:max_text] + ("..." if len(c.text) > max_text else "")
        line = f"  {c.id} -> {partner}  "
        line += _c(f"{c.classification:9s}", col)
        line += f"  drift={c.drift_score:6.2f}  {text}"
        print(line)


def _print_pairs(pairs) -> None:
    print(_c("hover-connector pairs (kept after split):", _BOLD))
    if not pairs:
        print(_c("  (none)", _DIM))
        return
    for p in pairs:
        col = _COLOR_BY_CLASS.get(p.classification, _RESET)
        line = f"  {p.before_id} <-> {p.after_id}  sim={p.similarity:.3f}  drift={p.drift_score:6.2f}  "
        line += _c(p.classification, col)
        print(line)


def _print_summary(summary) -> None:
    print(_c("summary:", _BOLD))
    s = summary
    print(f"  before/after counts:   {s.before_count} / {s.after_count}")
    counts_line = (
        _c(f"{s.unchanged} unchanged", _GREEN)
        + ", "
        + _c(f"{s.modified} modified", _YELLOW)
        + ", "
        + _c(f"{s.added} added", _BLUE)
        + ", "
        + _c(f"{s.removed} removed", _RED)
    )
    print(f"  classifications:       {counts_line}")
    print(f"  overall drift:         {s.overall_drift:6.2f}  (length-weighted, 0-100)")
    print(f"  pct text edited:       {s.pct_text_edited:6.2f}  (Levenshtein)")
    print(f"  pct meaning edited:    {s.pct_meaning_edited:6.2f}")
    print(_c(f"  models: {s.embedding_model} + {s.chat_model} | alignment={s.alignment} | {s.elapsed_ms} ms", _DIM))


def _print_concepts(concepts, status: str) -> None:
    label = f"concepts ({len(concepts)}, status={status}):"
    print(_c(label, _BOLD))
    if not concepts:
        print(_c("  (none)", _DIM))
        return
    for c in concepts:
        evidence = c.evidence[:60] + ("..." if len(c.evidence) > 60 else "")
        print(f"  [{c.status:13s}] {c.name}")
        print(_c(f'    "{evidence}"', _DIM))


def render(result: DiffResponse) -> None:
    _print_section("before clauses")
    _print_clauses("", result.before_clauses)

    _print_section("after clauses")
    _print_clauses("", result.after_clauses)

    _print_section("pairs")
    _print_pairs(result.pairs)

    _print_section("summary")
    _print_summary(result.summary)

    _print_section("concepts")
    _print_concepts(result.concepts, result.concept_extraction)


# ---------- Entry point -----------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the ML diff pipeline end-to-end.")
    p.add_argument(
        "--mock",
        action="store_true",
        help="Use deterministic mock embeddings + concepts. No API keys needed.",
    )
    p.add_argument(
        "--before",
        default=SAMPLE_BEFORE,
        help="Original document text. Defaults to the canned sample.",
    )
    p.add_argument(
        "--after",
        default=SAMPLE_AFTER,
        help="Revised document text. Defaults to the canned sample.",
    )
    return p.parse_args()


async def _run(args: argparse.Namespace) -> int:
    if args.mock:
        _install_mocks()
        print(_c("[mock mode — no OpenAI calls]", _GREY))
    else:
        if not os.getenv("OPENAI_API_KEY"):
            print(
                _c(
                    "OPENAI_API_KEY not set. Re-run with --mock for an offline demo.",
                    _RED,
                ),
                file=sys.stderr,
            )
            return 2
        print(_c("[live mode — real OpenAI calls]", _GREY))

    print()
    print(_c("BEFORE:", _BOLD), args.before[:200] + ("..." if len(args.before) > 200 else ""))
    print(_c("AFTER: ", _BOLD), args.after[:200] + ("..." if len(args.after) > 200 else ""))

    result = await pipeline_mod.run_diff(args.before, args.after)
    render(result)
    return 0


def main() -> int:
    return asyncio.run(_run(_parse_args()))


if __name__ == "__main__":
    sys.exit(main())
