from langchain_core.tools import tool
from backend.app.data.faq import faq

@tool
def search_faq(question: str) -> str:
    """Search the FAQ / product catalog for an answer to the customer's question."""
    q = question.lower()
    best, best_score = None, 0
    for number in range(1, 6):
        faq_question = faq[f"q{number}"]
        score = sum(1 for word in faq_question.lower().replace("?", "").split() if word in q)
        if score > best_score:
            best, best_score = faq[f"a{number}"], score
    if best is None:
        return "NO_MATCH"
    return best
