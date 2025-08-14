from pydantic import BaseModel, Field
try:
    from pydantic import EmailStr
except ImportError:
    # Fallback if email validation not available
    EmailStr = str
from typing import Optional, List
from datetime import datetime

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

class MerchantRegistration(BaseModel):
    business_name: str = Field(..., example="Manzini Grocery Store")
    business_type: str = Field(..., example="grocery")
    owner_name: str = Field(..., example="John Dlamini")
    phone: str = Field(..., example="+268 7612 3456")
    email: str = Field(..., example="john@manzinigrocery.sz")
    address: str = Field(..., example="123 Main Street, Manzini, Eswatini")
    id_number: str = Field(..., example="1234567890123")
    bank_account: Optional[str] = Field(None, example="1234567890")

class MerchantResponse(BaseModel):
    merchant_id: str
    business_name: str
    status: str
    api_key: str
    message: str

class QRCodeRequest(BaseModel):
    amount: Optional[float] = Field(None, example=100.0)
    description: Optional[str] = Field(None, example="Product purchase")
    expires_in_minutes: Optional[int] = Field(5, example=5)
    max_usage: Optional[int] = Field(1, example=1)

class QRCodeResponse(BaseModel):
    qr_code_id: str
    qr_code_data: str
    qr_code_url: str
    expires_at: Optional[datetime]
    is_dynamic: bool

class PaymentInitiation(BaseModel):
    qr_code_id: Optional[str] = Field(None, example="QR_123456")
    merchant_id: str = Field(..., example="MERCH_001")
    amount: float = Field(..., gt=0, example=50.0)
    customer_id: str = Field(..., example="CUST_001")
    payment_method: str = Field(..., example="qr_code")