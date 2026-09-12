"""End-to-end smoke test for the UniAgent backend.

Runs the full pipeline against the bundled sample PDF:
    PDF -> extract -> store -> index -> retrieve -> [Gemini -> reply]

The Gemini step only runs when GEMINI_API_KEY is set (via env var or .env).
Without a key, the test stops after retrieval and prints the top match so the
non-LLM pipeline can be verified offline.

Usage:
    python tests/e2e_sample_pdf.py ["optional question"] [--no-gemini]
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.config import Config
from backend.document_processor import process_document
from backend.document_store import add_document, clear_store, document_store


PDF_NAME = (
    "Object-Oriented Programming in C++ (4th Edition) by "
    "Robert Lafore.www.eeeuniversity.com.pdf"
)


def main(question: str = "What is C++ object-oriented programming?",
         use_gemini: bool | None = None) -> int:
    if use_gemini is None:
        use_gemini = bool(os.getenv("GEMINI_API_KEY") or Config.GEMINI_API_KEY)

    pdf = ROOT / "data" / PDF_NAME
    if not pdf.is_file():
        print(f"ERROR: sample PDF not found at {pdf}")
        return 1

    print(f"[1/4] Processing PDF: {pdf.name}")
    doc = process_document(pdf)
    print(f"      -> {len(doc.pages)} pages, {len(doc.get_text())} chars of text")

    print("[2/4] Adding document to store")
    clear_store()
    add_document(doc)
    print(f"      -> store now holds {len(document_store)} document(s)")

    print("[3/4] Retrieving relevant documents")
    from backend.retriever import retrieve
    results = retrieve(question, top_k=3)
    print(f"      Q: {question}")
    if not results:
        print("      -> no relevant documents matched")
    for rank, (matched, score) in enumerate(results, start=1):
        print(f"      #{rank} {matched.title!r} (score={score:.4f})")

    if not use_gemini:
        print("\nSkipping LLM step (GEMINI_API_KEY not set). "
              "Retrieval pipeline OK.")
        return 0

    print("[4/4] Asking through the conversation manager")
    from backend.conversation import Conversation, ConversationManager
    manager = ConversationManager()
    conv = manager.create("student")
    print(f"      Q: {question}")
    response = conv.ask(question)

    print("      Grounded:", response.grounded)
    print("      Sources: ", [s.document for s in response.sources])
    print("      Answer:")
    print(f"      {response.answer}")

    print("\nE2E test passed.")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    no_gemini = "--no-gemini" in args
    args = [a for a in args if a != "--no-gemini"]
    question = " ".join(args) or "What is C++ object-oriented programming?"
    raise SystemExit(main(question, use_gemini=False if no_gemini else None))