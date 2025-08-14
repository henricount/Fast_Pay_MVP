import asyncio
import random
from datetime import datetime
from typing import Dict, List
from app.models.schemas import PaymentRequest, RiskAssessment

class RiskEngine:
    """Fraud detection and risk assessment"""

    def __init__(self):
        self.merchant_profiles: Dict = {}
        self.suspicious_patterns = {
            "high_amount_threshold": 5000,
            "unusual_hours": [0, 1, 2, 3, 4, 5],  # Late night transactions
            "high_frequency_minutes": 5,
            "max_daily_amount": 50000
        }

    async def assess_risk(self, payment_data: PaymentRequest, payment_id: str) -> RiskAssessment:
        """Comprehensive risk assessment"""
        await asyncio.sleep(0.5)  # Simulate ML model processing time

        risk_factors = []
        risk_score = 0.0

        # Amount-based risk
        if payment_data.amount > self.suspicious_patterns["high_amount_threshold"]:
            risk_factors.append(f"High amount: {payment_data.amount} SZL")
            risk_score += 0.3

        # Time-based risk
        current_hour = datetime.utcnow().hour
        if current_hour in self.suspicious_patterns["unusual_hours"]:
            risk_factors.append(f"Unusual transaction time: {current_hour}:00")
            risk_score += 0.2

        # Merchant history simulation
        if payment_data.merchant_id not in self.merchant_profiles:
            risk_factors.append("New merchant - limited history")
            risk_score += 0.1
        else:
            # Simulate velocity check
            if random.random() < 0.1:  # 10% chance of velocity flag
                risk_factors.append("High transaction velocity detected")
                risk_score += 0.4

        # Location-based risk (mock)
        if payment_data.customer_location and payment_data.customer_location not in ["Manzini", "Mbabane"]:
            risk_factors.append(f"Unusual location: {payment_data.customer_location}")
            risk_score += 0.15

        # Random ML simulation - real system would use trained models
        ml_anomaly_score = random.uniform(0, 0.3)
        risk_score += ml_anomaly_score

        # Cap at 1.0
        risk_score = min(risk_score, 1.0)

        # Determine recommendation
        if risk_score < 0.3:
            recommendation = "APPROVE"
        elif risk_score < 0.7:
            recommendation = "REVIEW"
        else:
            recommendation = "DECLINE"

        return RiskAssessment(
            payment_id=payment_id,
            risk_score=round(risk_score, 3),
            risk_factors=risk_factors,
            recommendation=recommendation
        )