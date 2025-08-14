import asyncio
import random
import uuid
from typing import Dict
from app.models.schemas import PaymentRequest
from app.models.database import SettlementRail

class PaymentOrchestrator:
    """Routes payments and manages settlement"""

    def __init__(self):
        self.settlement_configs = {
            SettlementRail.ESWATINI_SWITCH: {
                "max_amount": 10000,
                "currencies": ["SZL"],
                "fee_rate": 0.015
            },
            SettlementRail.VISA_DIRECT: {
                "max_amount": 100000,
                "currencies": ["SZL", "USD", "EUR"],
                "fee_rate": 0.025
            }
        }

    def select_settlement_rail(self, payment_data: PaymentRequest, risk_score: float) -> SettlementRail:
        """Smart routing based on amount, currency, and risk"""

        # High risk transactions go to more secure rail
        if risk_score > 0.7:
            return SettlementRail.VISA_DIRECT

        # Local currency small amounts go to local switch
        if (payment_data.currency == "SZL" and
            payment_data.amount <= self.settlement_configs[SettlementRail.ESWATINI_SWITCH]["max_amount"]):
            return SettlementRail.ESWATINI_SWITCH

        return SettlementRail.VISA_DIRECT

    async def process_settlement(self, payment_data: PaymentRequest, settlement_rail: SettlementRail) -> Dict:
        """Process payment through selected settlement rail"""

        if settlement_rail == SettlementRail.ESWATINI_SWITCH:
            return await self._process_eswatini_switch(payment_data)
        else:
            return await self._process_visa_direct(payment_data)

    async def _process_eswatini_switch(self, payment_data: PaymentRequest) -> Dict:
        """Mock Eswatini National Payment Switch"""
        await asyncio.sleep(random.uniform(1, 3))  # Simulate network delay

        # 95% success rate for local switch
        if random.random() < 0.95:
            fee = payment_data.amount * self.settlement_configs[SettlementRail.ESWATINI_SWITCH]["fee_rate"]
            return {
                "status": "completed",
                "transaction_id": f"ESW_{uuid.uuid4().hex[:8].upper()}",
                "settlement_time": "T+0",
                "fee": round(fee, 2),
                "net_amount": round(payment_data.amount - fee, 2),
                "rail": "Eswatini National Payment Switch"
            }
        else:
            return {
                "status": "failed",
                "error_code": "INSUFFICIENT_FUNDS",
                "message": "Transaction declined by issuing bank",
                "rail": "Eswatini National Payment Switch"
            }

    async def _process_visa_direct(self, payment_data: PaymentRequest) -> Dict:
        """Mock Visa Direct processing"""
        await asyncio.sleep(random.uniform(2, 4))  # Simulate international processing

        # 92% success rate for international
        if random.random() < 0.92:
            fee = payment_data.amount * self.settlement_configs[SettlementRail.VISA_DIRECT]["fee_rate"]
            return {
                "status": "completed",
                "transaction_id": f"VD_{uuid.uuid4().hex[:8].upper()}",
                "settlement_time": "T+1",
                "fee": round(fee, 2),
                "net_amount": round(payment_data.amount - fee, 2),
                "rail": "Visa Direct"
            }
        else:
            return {
                "status": "failed",
                "error_code": "NETWORK_ERROR",
                "message": "Temporary network issue, please retry",
                "rail": "Visa Direct"
            }