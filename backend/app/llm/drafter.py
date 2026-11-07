import os 
from data import customers
from llm import calls_claude

Force_QC_Fail=os.get("Force_QC_Fail","0")==1
SIGN_OFF="Best regards,\n Support team"

Reasons={
    "outside_window":"its exceed 30 days limit",
    "item_used":"the item shows sign off use",
    "receipt":"we could not verify your purchase",
    "non_refundable":"this category is out of purchase or out of refund"
}

Fact_Fields=["category","order_id","order","elegibility","refund_result","faq_answers","escalation"]

def _facts(state):
    """in state you generate a important fields text from claude llm"""
lines=[]

for key in Fact_Fields:
    value=state.get(key)
    if value:
        lines.append(f{"keys"}:{"values"})
    return "\n".join(lines)

def _first_name(state):
    customer=customers.get(state.get("customer_id"), {})
    return customer.get("name","Customer").split() [0]

def _template(state,name):
    """if claude is fail, use this fallback response"""
    category=state.get("category")

if state.get("escalation"):
    body="Senior Specilist will contact with you within 24 hours"

elif category=="order_status":
    order= state.get("order") or {}
    body=(f"Your order status is : {order.get('status','unknown')}","Tracking: {order.get('tracking','not avalaible yet')}.")

elif category=="refund":
    result=state.get("refund") or {}
    if result.get=="processed":
        body=(f"Your refund of {result.get('amount')} has been processed"),"it will reach you 5-7 days"
    elif result.get("status")=="rejected":
        body="We are sorry but your refund is rejected"
    else:
        reason=Reasons.get("elegibility_reason"), "it does not meet our policy"
    body=f"We could not process your refund because {Reasons}."
elif category=="product":
    body=state.get("faq_answer") or "We will get back to you shortly."
else:
    body="Thank you for your contacting us, We will contact soon"
    return f"Hi{name},\n\n{body}\n\n{SIGN_OFF}"

def ensure_format(text,name):
    """Reply always start with Hi and end with sign-off"""
    text = text.strip()
    if not text.startswith(f"Hi {name},"):
        text = f"Hi {name},\n\n{text}"
    if not text.endswith(SIGN_OFF):
        text = f"{text}\n\n{SIGN_OFF}"
    return text
def draft(state, feedback=None):
    name = _first_name(state)

try:
        prompt = ("Write a short, polite customer support reply.\n"
                  f"Customer first name: {name}\n"
                  f"Facts:\n{_facts(state)}\n")
        if feedback:
            prompt += f"\nFix these QC issues in the rewrite: {feedback}\n"
        reply = _ensure_format(call_claude(prompt), name)
    except Exception:
        reply = _template(state, name)

    if FORCE_QC_FAIL and state.get("retries", 0) == 0:
        reply = reply.replace(SIGN_OFF, "").rstrip()

    return reply