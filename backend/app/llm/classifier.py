import json
import re
from typing import Literal

from .client import _ask, _json


Category = Literal["refund", "product", "order_status", "other"]
Sentiment = Literal["Angry", "Negative", "Positive", "Neutral"]

_CATEGORY_MAP: dict[str, Category] = {
    "refund": "refund",
    "product": "product",
    "order_status": "order_status",
    "other": "other",
}
_SENTIMENT_VALUES = {"angry": "Angry", "negative": "Negative", "positive": "Positive", "neutral": "Neutral"}


def extract_order_id(text: str) -> str | None:
    """Extract the number from #1001, ORD-1001, or order 1001."""
    match = re.search(r"(?<![A-Za-z0-9])(?:#\s*|ORD-\s*|order\s+#?\s*)(\d+)\b", text, re.IGNORECASE)
    return match.group(1) if match else None


def _pattern_sentiment(message: str) -> Sentiment:
    message_without_order_id = re.sub(
        r"\bORD-\d+\b|#\d+|\border\s+#?\d+\b", "", message, flags=re.IGNORECASE
    )
    letters = [character for character in message_without_order_id if character.isalpha()]
    is_all_caps = bool(letters) and all(character.isupper() for character in letters)
    if is_all_caps or re.search(
        r"\b(angry|unacceptable|furious|ridiculous|scam|worst|terrible)\b",
        message,
        re.IGNORECASE,
    ):
        return "Angry"
    if re.search(r"\b(disappointed|frustrated|broken|late)\b", message, re.IGNORECASE):
        return "Negative"
    if re.search(r"\b(thank|great|love)\b", message, re.IGNORECASE):
        return "Positive"
    return "Neutral"


def _pattern_category(message: str) -> Category:
    text = message.casefold()
    if re.search(r"\b(refund|money back|return)\b", text):
        return "refund"
    if re.search(r"\b(waterproof|battery|warranty|compatible|how long does)\b", text):
        return "product"
    if re.search(r"\b(where is|track|shipped|update on|my order|that order)\b", text):
        return "order_status"
    return "other"


def classify(message: str, history: object = None) -> dict[str, str | None]:
    """Classify a message with the LLM when possible, then fall back to patterns."""
    fallback_category = _pattern_category(message)
    fallback_sentiment = _pattern_sentiment(message)

    prompt = (
        "Classify the customer message. Return only a JSON object with "
        '"category" (refund, product, order_status, or other) and '
        '"sentiment" (Angry, Negative, Positive, or Neutral). '
        "Do not include an order_id.\n"
        f"{json.dumps({'message': message, 'history': history}, ensure_ascii=False, default=str)}"
    )
    parsed = _json(_ask("You are a customer-support message classifier.", prompt))

    category = fallback_category
    sentiment = fallback_sentiment
    if isinstance(parsed, dict):
        llm_category = parsed.get("category")
        if isinstance(llm_category, str) and llm_category.casefold() in _CATEGORY_MAP:
            category = _CATEGORY_MAP[llm_category.casefold()]
            llm_sentiment = parsed.get("sentiment")
            if isinstance(llm_sentiment, str):
                sentiment = _SENTIMENT_VALUES.get(llm_sentiment.casefold(), fallback_sentiment)

    return {
        "category": category,
        "sentiment": sentiment,
        "order_id": extract_order_id(message),
    }
