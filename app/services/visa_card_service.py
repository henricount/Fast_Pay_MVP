import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.service_providers import VisaCard, CardTransaction
import hashlib
import json
from cryptography.fernet import Fernet
import os

class VisaCardService:
    """Service for managing Visa prepaid cards"""
    
    def __init__(self):
        # In production, store this securely
        self.encryption_key = os.getenv('CARD_ENCRYPTION_KEY', Fernet.generate_key())
        self.cipher = Fernet(self.encryption_key)
    
    def generate_card_number(self) -> str:
        """Generate a valid Visa card number"""
        # Visa cards start with 4
        prefix = "4532"  # Test Visa prefix
        
        # Generate 12 random digits
        middle_digits = ''.join(secrets.choice(string.digits) for _ in range(12))
        
        # Calculate Luhn check digit
        card_without_check = prefix + middle_digits
        check_digit = self._calculate_luhn_check_digit(card_without_check)
        
        return card_without_check + str(check_digit)
    
    def _calculate_luhn_check_digit(self, card_number: str) -> int:
        """Calculate Luhn algorithm check digit"""
        digits = [int(d) for d in card_number]
        
        # Double every second digit from right
        for i in range(len(digits) - 2, -1, -2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] = digits[i] // 10 + digits[i] % 10
        
        total = sum(digits)
        return (10 - (total % 10)) % 10
    
    def generate_cvv(self) -> str:
        """Generate a 3-digit CVV"""
        return ''.join(secrets.choice(string.digits) for _ in range(3))
    
    def generate_expiry_date(self, years_valid: int = 3) -> str:
        """Generate expiry date (MM/YYYY format)"""
        expiry = datetime.now() + timedelta(days=365 * years_valid)
        return expiry.strftime("%m/%Y")
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive card data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive card data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    def issue_card(self, customer_id: str, card_request: Dict, db: Session) -> Dict:
        """Issue a new Visa prepaid card"""
        
        # Generate card details
        card_number = self.generate_card_number()
        cvv = self.generate_cvv()
        expiry_date = self.generate_expiry_date()
        
        # Generate card ID
        card_id = f"CARD_{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))}"
        
        # Encrypt sensitive data
        encrypted_card_number = self.encrypt_sensitive_data(card_number)
        encrypted_cvv = self.encrypt_sensitive_data(cvv)
        
        # Set limits based on card type
        daily_limit, monthly_limit = self._get_card_limits(card_request.get('card_variant', 'physical'))
        
        # Create card record
        visa_card = VisaCard(
            card_id=card_id,
            customer_id=customer_id,
            card_number_encrypted=encrypted_card_number,
            card_type='prepaid',
            card_variant=card_request.get('card_variant', 'physical'),
            cardholder_name=card_request['cardholder_name'],
            expiry_date=expiry_date,
            cvv_encrypted=encrypted_cvv,
            balance=0.00,
            available_balance=0.00,
            daily_limit=daily_limit,
            monthly_limit=monthly_limit,
            international_enabled=card_request.get('international_enabled', False),
            status='active'
        )
        
        db.add(visa_card)
        db.commit()
        db.refresh(visa_card)
        
        # Return card details (masked for security)
        return {
            "card_id": card_id,
            "card_number_masked": self._mask_card_number(card_number),
            "cardholder_name": card_request['cardholder_name'],
            "expiry_date": expiry_date,
            "card_variant": card_request.get('card_variant', 'physical'),
            "daily_limit": daily_limit,
            "monthly_limit": monthly_limit,
            "status": "active",
            "international_enabled": card_request.get('international_enabled', False),
            "issued_date": datetime.now().isoformat(),
            "message": "Visa prepaid card issued successfully"
        }
    
    def _get_card_limits(self, card_variant: str) -> tuple:
        """Get spending limits based on card variant"""
        limits = {
            'youth': (1000.00, 5000.00),      # Youth cards have lower limits
            'physical': (5000.00, 50000.00),  # Standard physical cards
            'virtual': (3000.00, 30000.00),   # Virtual cards - slightly lower
            'corporate': (10000.00, 100000.00) # Corporate cards - higher limits
        }
        return limits.get(card_variant, (5000.00, 50000.00))
    
    def _mask_card_number(self, card_number: str) -> str:
        """Mask card number for display (show first 4 and last 4 digits)"""
        return f"{card_number[:4]}****{card_number[-4:]}"
    
    def load_card_balance(self, card_id: str, amount: float, db: Session) -> Dict:
        """Load money onto a prepaid card"""
        card = db.query(VisaCard).filter(VisaCard.card_id == card_id).first()
        
        if not card:
            raise ValueError("Card not found")
        
        if card.status != 'active':
            raise ValueError("Card is not active")
        
        # Update card balance
        card.balance += amount
        card.available_balance += amount
        
        # Create transaction record
        transaction_id = f"TXN_{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))}"
        
        transaction = CardTransaction(
            transaction_id=transaction_id,
            card_id=card_id,
            transaction_type='top_up',
            amount=amount,
            status='approved',
            merchant_name='Fast Pay Top-Up',
            authorization_code=f"AUTH_{''.join(secrets.choice(string.digits) for _ in range(6))}",
            reference_number=transaction_id,
            processed_at=datetime.now()
        )
        
        db.add(transaction)
        db.commit()
        
        return {
            "transaction_id": transaction_id,
            "card_id": card_id,
            "amount_loaded": amount,
            "new_balance": card.balance,
            "available_balance": card.available_balance,
            "transaction_date": datetime.now().isoformat(),
            "status": "completed"
        }
    
    def process_card_transaction(self, transaction_data: Dict, db: Session) -> Dict:
        """Process a card transaction (purchase, withdrawal, etc.)"""
        card_id = transaction_data['card_id']
        amount = transaction_data['amount']
        transaction_type = transaction_data.get('transaction_type', 'purchase')
        
        card = db.query(VisaCard).filter(VisaCard.card_id == card_id).first()
        
        if not card:
            raise ValueError("Card not found")
        
        # Validate transaction
        validation_result = self._validate_transaction(card, amount, transaction_data)
        if not validation_result['valid']:
            return {
                "status": "declined",
                "reason": validation_result['reason'],
                "transaction_id": None
            }
        
        # Process transaction
        transaction_id = f"TXN_{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))}"
        
        # Update card balance
        if transaction_type in ['purchase', 'withdrawal']:
            card.available_balance -= amount
            card.total_transactions += 1
            card.total_spent += amount
        
        card.last_used = datetime.now()
        
        # Create transaction record
        transaction = CardTransaction(
            transaction_id=transaction_id,
            card_id=card_id,
            transaction_type=transaction_type,
            amount=amount,
            merchant_name=transaction_data.get('merchant_name', 'Unknown Merchant'),
            merchant_category=transaction_data.get('merchant_category'),
            merchant_location=transaction_data.get('merchant_location'),
            merchant_country=transaction_data.get('merchant_country', 'Eswatini'),
            authorization_code=f"AUTH_{''.join(secrets.choice(string.digits) for _ in range(6))}",
            reference_number=transaction_data.get('reference_number', transaction_id),
            status='approved',
            is_international=transaction_data.get('merchant_country', 'Eswatini') != 'Eswatini',
            risk_score=validation_result.get('risk_score', 0.1),
            processed_at=datetime.now()
        )
        
        db.add(transaction)
        db.commit()
        
        return {
            "transaction_id": transaction_id,
            "status": "approved",
            "amount": amount,
            "available_balance": card.available_balance,
            "authorization_code": transaction.authorization_code,
            "transaction_date": datetime.now().isoformat(),
            "merchant_name": transaction_data.get('merchant_name', 'Unknown Merchant')
        }
    
    def _validate_transaction(self, card: VisaCard, amount: float, transaction_data: Dict) -> Dict:
        """Validate transaction against card limits and status"""
        
        # Check card status
        if card.status != 'active':
            return {"valid": False, "reason": "Card is not active"}
        
        # Check available balance
        if amount > card.available_balance:
            return {"valid": False, "reason": "Insufficient funds"}
        
        # Check daily limit
        today = datetime.now().date()
        daily_spent = self._get_daily_spending(card.card_id, today)
        if daily_spent + amount > card.daily_limit:
            return {"valid": False, "reason": "Daily limit exceeded"}
        
        # Check monthly limit
        this_month = datetime.now().replace(day=1).date()
        monthly_spent = self._get_monthly_spending(card.card_id, this_month)
        if monthly_spent + amount > card.monthly_limit:
            return {"valid": False, "reason": "Monthly limit exceeded"}
        
        # Check international transactions
        is_international = transaction_data.get('merchant_country', 'Eswatini') != 'Eswatini'
        if is_international and not card.international_enabled:
            return {"valid": False, "reason": "International transactions not enabled"}
        
        # Calculate risk score (simple implementation)
        risk_score = self._calculate_risk_score(card, amount, transaction_data)
        
        return {
            "valid": True,
            "risk_score": risk_score
        }
    
    def _get_daily_spending(self, card_id: str, date) -> float:
        """Get total spending for a specific day"""
        # This would query the database for transactions on the given date
        # Simplified for demo
        return 0.0
    
    def _get_monthly_spending(self, card_id: str, month_start) -> float:
        """Get total spending for the current month"""
        # This would query the database for transactions in the current month
        # Simplified for demo
        return 0.0
    
    def _calculate_risk_score(self, card: VisaCard, amount: float, transaction_data: Dict) -> float:
        """Calculate transaction risk score (0.0 = low risk, 1.0 = high risk)"""
        risk_score = 0.0
        
        # Large transaction risk
        if amount > card.daily_limit * 0.5:
            risk_score += 0.3
        
        # International transaction risk
        if transaction_data.get('merchant_country', 'Eswatini') != 'Eswatini':
            risk_score += 0.2
        
        # Unusual merchant category
        high_risk_categories = ['gambling', 'adult_entertainment', 'crypto']
        if transaction_data.get('merchant_category') in high_risk_categories:
            risk_score += 0.4
        
        # Time-based risk (late night transactions)
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 23:
            risk_score += 0.1
        
        return min(risk_score, 1.0)
    
    def get_card_details(self, card_id: str, db: Session) -> Dict:
        """Get card details (masked for security)"""
        card = db.query(VisaCard).filter(VisaCard.card_id == card_id).first()
        
        if not card:
            raise ValueError("Card not found")
        
        # Decrypt and mask card number
        card_number = self.decrypt_sensitive_data(card.card_number_encrypted)
        masked_number = self._mask_card_number(card_number)
        
        return {
            "card_id": card.card_id,
            "card_number_masked": masked_number,
            "cardholder_name": card.cardholder_name,
            "expiry_date": card.expiry_date,
            "card_variant": card.card_variant,
            "balance": card.balance,
            "available_balance": card.available_balance,
            "daily_limit": card.daily_limit,
            "monthly_limit": card.monthly_limit,
            "status": card.status,
            "international_enabled": card.international_enabled,
            "total_transactions": card.total_transactions,
            "total_spent": card.total_spent,
            "last_used": card.last_used.isoformat() if card.last_used else None,
            "issued_date": card.issued_date.isoformat()
        }
    
    def get_card_transactions(self, card_id: str, limit: int = 50, db: Session = None) -> List[Dict]:
        """Get card transaction history"""
        transactions = db.query(CardTransaction).filter(
            CardTransaction.card_id == card_id
        ).order_by(CardTransaction.transaction_date.desc()).limit(limit).all()
        
        return [
            {
                "transaction_id": txn.transaction_id,
                "transaction_type": txn.transaction_type,
                "amount": txn.amount,
                "merchant_name": txn.merchant_name,
                "merchant_location": txn.merchant_location,
                "status": txn.status,
                "transaction_date": txn.transaction_date.isoformat(),
                "authorization_code": txn.authorization_code,
                "is_international": txn.is_international
            }
            for txn in transactions
        ]
    
    def block_card(self, card_id: str, reason: str, db: Session) -> Dict:
        """Block a card"""
        card = db.query(VisaCard).filter(VisaCard.card_id == card_id).first()
        
        if not card:
            raise ValueError("Card not found")
        
        card.status = 'blocked'
        db.commit()
        
        return {
            "card_id": card_id,
            "status": "blocked",
            "reason": reason,
            "blocked_at": datetime.now().isoformat()
        }
    
    def unblock_card(self, card_id: str, db: Session) -> Dict:
        """Unblock a card"""
        card = db.query(VisaCard).filter(VisaCard.card_id == card_id).first()
        
        if not card:
            raise ValueError("Card not found")
        
        card.status = 'active'
        db.commit()
        
        return {
            "card_id": card_id,
            "status": "active",
            "unblocked_at": datetime.now().isoformat()
        }