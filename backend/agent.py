def _build_prompt(question: str, retrieved_docs: List[Tuple[object, float]]) -> str:
    # Relaxed the prompt to allow general knowledge fallback for BSAI concepts
    system_prompt = (
        "You are an expert AI academic co-pilot for BSAI students. "
        "Use the provided document context to answer the user's question comprehensively. "
        "If the specific detail is missing from the provided text, use your broad knowledge of "
        "Artificial Intelligence, Computer Science, and Mathematics to explain the concept to the student."
    )
    snippets = []
    for doc, _score in retrieved_docs:
        # Increased chunk size from 2,000 to 40,000 characters to bypass title/copyright pages
        snippets.append(f"Document: {doc.title}\n{doc.get_text()[:40000]}\n---")
    
    context = "\n".join(snippets)
    return f"{system_prompt}\n\nContext:\n{context}\n\nQuestion: {question}"
