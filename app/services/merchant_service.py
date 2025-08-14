import secrets
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.database import Merchant, QRCode, MerchantStatus, BusinessType
from app.models.schemas import MerchantRegistration, QRCodeRequest
import json
import base64

class MerchantService:
    """Handles merchant registration, authentication, and QR code generation"""

    def __init__(self):
        self.business_types = {
            "retail": BusinessType.RETAIL,
            "restaurant": BusinessType.RESTAURANT, 
            "grocery": BusinessType.GROCERY,
            "service": BusinessType.SERVICE,
            "online": BusinessType.ONLINE,
            "other": BusinessType.OTHER
        }

    def generate_merchant_id(self, business_name: str) -> str:
        """Generate unique merchant ID"""
        # Clean business name
        clean_name = ''.join(c.upper() for c in business_name if c.isalnum())[:10]
        # Add random suffix
        suffix = ''.join(secrets.choice(string.digits) for _ in range(3))
        return f"MERCH_{clean_name}_{suffix}"

    def generate_api_credentials(self) -> tuple[str, str]:
        """Generate API key and secret"""
        api_key = f"fpk_{''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))}"
        api_secret = f"fps_{''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(48))}"
        return api_key, api_secret

    def register_merchant(self, registration: MerchantRegistration, db: Session) -> Merchant:
        """Register new merchant"""
        
        # Check if email already exists
        existing = db.query(Merchant).filter(Merchant.email == registration.email).first()
        if existing:
            raise ValueError("Merchant with this email already exists")

        # Generate credentials
        merchant_id = self.generate_merchant_id(registration.business_name)
        api_key, api_secret = self.generate_api_credentials()

        # Create merchant
        merchant = Merchant(
            merchant_id=merchant_id,
            business_name=registration.business_name,
            business_type=self.business_types.get(registration.business_type, BusinessType.OTHER),
            owner_name=registration.owner_name,
            phone=registration.phone,
            email=registration.email,
            address=registration.address,
            id_number=registration.id_number,
            bank_account=registration.bank_account,
            api_key=api_key,
            api_secret=api_secret,
            status=MerchantStatus.APPROVED,  # Auto-approve for demo
            fee_rate=0.02
        )

        db.add(merchant)
        db.commit()
        db.refresh(merchant)

        return merchant

    def authenticate_merchant(self, api_key: str, db: Session) -> Merchant:
        """Authenticate merchant by API key"""
        merchant = db.query(Merchant).filter(
            Merchant.api_key == api_key,
            Merchant.status == MerchantStatus.APPROVED,
            Merchant.is_active == True
        ).first()
        
        if not merchant:
            raise ValueError("Invalid API key or inactive merchant")
        
        return merchant

    def authenticate_merchant_id(self, merchant_id: str, db: Session) -> Merchant:
        """Authenticate merchant by merchant ID (for demo purposes)"""
        merchant = db.query(Merchant).filter(
            Merchant.merchant_id == merchant_id,
            Merchant.status == MerchantStatus.APPROVED,
            Merchant.is_active == True
        ).first()
        
        # If not found, check if it's a legacy demo merchant
        if not merchant and merchant_id.startswith("MERCH_"):
            return None  # Let legacy authentication handle it
        
        return merchant

    def generate_qr_code(self, merchant_id: str, qr_request: QRCodeRequest, db: Session) -> QRCode:
        """Generate QR code for merchant"""
        
        # Verify merchant exists
        merchant = self.authenticate_merchant_id(merchant_id, db)
        if not merchant:
            raise ValueError("Merchant not found")

        # Generate QR code ID
        qr_code_id = f"QR_{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))}"

        # Calculate expiry
        expires_at = None
        if qr_request.expires_in_minutes:
            expires_at = datetime.utcnow() + timedelta(minutes=qr_request.expires_in_minutes)

        # Create QR code record
        qr_code = QRCode(
            merchant_id=merchant_id,
            qr_code_id=qr_code_id,
            amount=qr_request.amount,
            description=qr_request.description,
            is_dynamic=qr_request.amount is None,
            expires_at=expires_at,
            max_usage=qr_request.max_usage,
            is_active=True
        )

        db.add(qr_code)
        db.commit()
        db.refresh(qr_code)

        return qr_code

    def generate_qr_data(self, qr_code: QRCode) -> str:
        """Generate QR code data string"""
        qr_data = {
            "qr_id": qr_code.qr_code_id,
            "merchant_id": qr_code.merchant_id,
            "amount": qr_code.amount,
            "description": qr_code.description,
            "expires_at": qr_code.expires_at.isoformat() if qr_code.expires_at else None,
            "system": "FastPay"
        }
        
        # Encode as base64 for QR code
        qr_json = json.dumps(qr_data)
        qr_encoded = base64.b64encode(qr_json.encode()).decode()
        
        return f"fastpay://{qr_encoded}"

    def validate_qr_code(self, qr_code_id: str, db: Session) -> QRCode:
        """Validate QR code for payment"""
        qr_code = db.query(QRCode).filter(
            QRCode.qr_code_id == qr_code_id,
            QRCode.is_active == True
        ).first()

        if not qr_code:
            raise ValueError("QR code not found or inactive")

        # Check expiry
        if qr_code.expires_at and datetime.utcnow() > qr_code.expires_at:
            raise ValueError("QR code has expired")

        # Check usage limit
        if qr_code.max_usage and qr_code.usage_count >= qr_code.max_usage:
            raise ValueError("QR code usage limit exceeded")

        return qr_code

    def increment_qr_usage(self, qr_code_id: str, db: Session):
        """Increment QR code usage count"""
        qr_code = db.query(QRCode).filter(QRCode.qr_code_id == qr_code_id).first()
        if qr_code:
            qr_code.usage_count += 1
            if qr_code.max_usage and qr_code.usage_count >= qr_code.max_usage:
                qr_code.is_active = False
            db.commit()

    def get_merchant_qr_codes(self, merchant_id: str, db: Session) -> list:
        """Get all QR codes for a merchant"""
        return db.query(QRCode).filter(
            QRCode.merchant_id == merchant_id,
            QRCode.is_active == True
        ).order_by(QRCode.created_at.desc()).all()