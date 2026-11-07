from pydantic import BaseModel

class Pending_Approval(BaseModel):
    ticket_id:int
    customer_id:int
    order_id:int
    amount:int
    message:str
    question:str

class Approval_Decision(BaseModel):
    approved:bool
    reviewer:str
    note:str

