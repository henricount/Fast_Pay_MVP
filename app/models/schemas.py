from pydantic import BaseModel, Field
from typing import Optional, List

class PaymentRequest(BaseModel):
    merchant_id: str = Field(..., example="MERCH_001")
    customer_id: str = Field(..., example="CUST_001")
    amount: float = Field(..., gt=0, example=1000.0)
    currency: str = Field(default="SZL", example="SZL")
    payment_method: str = Field(..., example="qr_code")
    customer_location: Optional[str] = Field(None, example="Manzini")

class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    message: str
    estimated_completion: Optional[str] = None

class RiskAssessment(BaseModel):
    payment_id: str
    risk_score: float
    risk_factors: List[str]
    recommendation: str