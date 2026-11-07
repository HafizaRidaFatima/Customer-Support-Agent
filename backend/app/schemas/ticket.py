from pydantic import BaseModel

class TicketResult(BaseModel):
    ticket_id:str
    customer_id:str
    category:str
    sentiment:str
    path:str
    final_reply:str
    refund_result:str
    escalation:str
    review:str
    retries:str

class StreamEvent(BaseModel):
    type:str
    nodes:str
    update:str
    payload:str
    result:str
    detail:str

class Outcome(BaseModel):
    status:str
    result:str
    pending:str