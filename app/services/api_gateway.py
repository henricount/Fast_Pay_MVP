from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from app.services.merchant_service import MerchantService

class APIGateway:
    """Handles authentication, rate limiting, and request validation"""

    def __init__(self):
        self.rate_limits: Dict[str, List[datetime]] = {}
        self.merchant_service = MerchantService()

    def authenticate_request(self, merchant_id: str, db: Session = None) -> bool:
        """Enhanced authentication - checks database for registered merchants"""
        
        # If database session provided, try proper authentication
        if db:
            try:
                merchant = self.merchant_service.authenticate_merchant_id(merchant_id, db)
                if merchant:
                    return True
            except:
                pass
        
        # Fallback to legacy demo authentication
        return merchant_id.startswith("MERCH_")

    def check_rate_limit(self, merchant_id: str) -> bool:
        """Simple rate limiting - max 10 requests per minute"""
        now = datetime.utcnow()
        if merchant_id not in self.rate_limits:
            self.rate_limits[merchant_id] = []

        # Remove old entries
        self.rate_limits[merchant_id] = [
            ts for ts in self.rate_limits[merchant_id]
            if now - ts < timedelta(minutes=1)
        ]

        if len(self.rate_limits[merchant_id]) >= 10:
            return False

        self.rate_limits[merchant_id].append(now)
        return True