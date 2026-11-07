from pydantic import BaseModel

class Customer_Out(BaseModel):
    customer_id: str
    name: str