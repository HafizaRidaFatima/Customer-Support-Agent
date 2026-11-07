from fastapi import APIRouter

from backend.app.data.customers import customers
from backend.app.schemas.customer import Customer_Out


router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[Customer_Out])
def list_customers() -> list[Customer_Out]:
    return customers
