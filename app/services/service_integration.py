import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.service_providers import (
    ServiceProvider, ServiceCategory, ServiceTransaction, 
    UtilityBilling, EducationPayment, HospitalityService
)
import secrets
import string

class ServiceIntegrationManager:
    """Central manager for all service provider integrations"""
    
    def __init__(self):
        self.providers = {}
        self.active_sessions = {}
    
    async def register_provider(self, provider_config: Dict) -> str:
        """Register a new service provider"""
        provider_id = f"PROV_{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))}"
        
        # Validate provider configuration
        required_fields = ['provider_name', 'provider_code', 'service_type', 'api_endpoint']
        for field in required_fields:
            if field not in provider_config:
                raise ValueError(f"Missing required field: {field}")
        
        self.providers[provider_id] = provider_config
        return provider_id
    
    async def process_service_payment(self, transaction_data: Dict, db: Session) -> Dict:
        """Process payment for any service provider"""
        provider_id = transaction_data.get('provider_id')
        provider = db.query(ServiceProvider).filter(ServiceProvider.provider_id == provider_id).first()
        
        if not provider:
            raise ValueError("Service provider not found")
        
        # Route to appropriate service handler
        if provider.service_type.value == 'utility':
            return await self._process_utility_payment(transaction_data, provider, db)
        elif provider.service_type.value == 'government':
            return await self._process_government_payment(transaction_data, provider, db)
        elif provider.service_type.value == 'education':
            return await self._process_education_payment(transaction_data, provider, db)
        elif provider.service_type.value == 'transport':
            return await self._process_transport_payment(transaction_data, provider, db)
        elif provider.service_type.value == 'hospitality':
            return await self._process_hospitality_payment(transaction_data, provider, db)
        else:
            raise ValueError(f"Unsupported service type: {provider.service_type}")

class UtilityServiceIntegration:
    """Handle utility service payments (EWSC, EEC)"""
    
    async def get_customer_balance(self, provider_code: str, customer_id: str) -> Dict:
        """Get current utility account balance"""
        if provider_code == "EWSC":
            return await self._get_water_balance(customer_id)
        elif provider_code == "EEC":
            return await self._get_electricity_balance(customer_id)
        else:
            raise ValueError(f"Unsupported utility provider: {provider_code}")
    
    async def _get_water_balance(self, account_number: str) -> Dict:
        """Get EWSC water account balance"""
        # Simulate EWSC API call
        return {
            "account_number": account_number,
            "account_holder": "John Dlamini",
            "current_balance": 450.75,
            "last_reading_date": "2024-08-01",
            "current_reading": 1250.5,
            "previous_reading": 1220.3,
            "consumption": 30.2,
            "billing_period": "2024-08-01 to 2024-08-31",
            "due_date": "2024-09-15",
            "status": "active"
        }
    
    async def _get_electricity_balance(self, meter_number: str) -> Dict:
        """Get EEC electricity account balance"""
        # Simulate EEC API call
        return {
            "meter_number": meter_number,
            "account_holder": "John Dlamini",
            "current_balance": 125.50,
            "last_purchase_date": "2024-08-10",
            "last_purchase_amount": 200.00,
            "consumption_rate": "2.5 kWh/day",
            "estimated_days_remaining": 15,
            "tariff_rate": 0.85,
            "status": "active"
        }
    
    async def process_utility_payment(self, payment_data: Dict) -> Dict:
        """Process utility bill payment"""
        provider_code = payment_data.get('provider_code')
        
        if provider_code == "EWSC":
            return await self._process_water_payment(payment_data)
        elif provider_code == "EEC":
            return await self._process_electricity_payment(payment_data)
        else:
            raise ValueError(f"Unsupported utility provider: {provider_code}")
    
    async def _process_water_payment(self, payment_data: Dict) -> Dict:
        """Process EWSC water bill payment"""
        # Simulate EWSC payment processing
        return {
            "transaction_id": f"EWSC_{''.join(secrets.choice(string.digits) for _ in range(10))}",
            "status": "completed",
            "amount_paid": payment_data['amount'],
            "new_balance": max(0, payment_data.get('current_balance', 0) - payment_data['amount']),
            "receipt_number": f"RCP_{''.join(secrets.choice(string.digits) for _ in range(8))}",
            "payment_date": datetime.utcnow().isoformat(),
            "reference": f"Water payment for account {payment_data['account_number']}"
        }
    
    async def _process_electricity_payment(self, payment_data: Dict) -> Dict:
        """Process EEC electricity payment/top-up"""
        # Generate electricity tokens (simulated)
        token = ''.join(secrets.choice(string.digits) for _ in range(20))
        
        return {
            "transaction_id": f"EEC_{''.join(secrets.choice(string.digits) for _ in range(10))}",
            "status": "completed",
            "amount_paid": payment_data['amount'],
            "units_purchased": round(payment_data['amount'] / 0.85, 2),  # E0.85 per kWh
            "token": token,
            "token_expiry": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "new_balance": payment_data.get('current_balance', 0) + payment_data['amount'],
            "receipt_number": f"RCP_{''.join(secrets.choice(string.digits) for _ in range(8))}",
            "payment_date": datetime.utcnow().isoformat()
        }

class GovernmentServiceIntegration:
    """Handle government service payments (ERS, Police)"""
    
    async def get_tax_liability(self, taxpayer_id: str) -> Dict:
        """Get taxpayer liability from ERS"""
        # Simulate ERS API call
        return {
            "taxpayer_id": taxpayer_id,
            "taxpayer_name": "John Dlamini",
            "outstanding_amount": 2500.00,
            "last_payment_date": "2024-07-15",
            "payment_plan_active": False,
            "penalties": 125.00,
            "interest": 75.50,
            "total_due": 2700.50,
            "due_date": "2024-09-30",
            "tax_year": "2024"
        }
    
    async def get_police_fines(self, id_number: str) -> List[Dict]:
        """Get outstanding police fines"""
        # Simulate Police system API call
        return [
            {
                "fine_id": "FINE_2024_001234",
                "violation_type": "Speeding",
                "violation_date": "2024-08-05",
                "location": "Mbabane-Manzini Highway",
                "fine_amount": 500.00,
                "penalty_amount": 50.00,
                "total_amount": 550.00,
                "due_date": "2024-09-05",
                "status": "outstanding",
                "vehicle_registration": "SD 123 GP"
            },
            {
                "fine_id": "FINE_2024_001567",
                "violation_type": "Parking",
                "violation_date": "2024-08-12",
                "location": "Mbabane City Center",
                "fine_amount": 100.00,
                "penalty_amount": 0.00,
                "total_amount": 100.00,
                "due_date": "2024-09-12",
                "status": "outstanding",
                "vehicle_registration": "SD 123 GP"
            }
        ]
    
    async def process_government_payment(self, payment_data: Dict) -> Dict:
        """Process government service payment"""
        service_type = payment_data.get('service_type')
        
        if service_type == "tax_payment":
            return await self._process_tax_payment(payment_data)
        elif service_type == "fine_payment":
            return await self._process_fine_payment(payment_data)
        elif service_type == "license_renewal":
            return await self._process_license_payment(payment_data)
        else:
            raise ValueError(f"Unsupported government service: {service_type}")
    
    async def _process_tax_payment(self, payment_data: Dict) -> Dict:
        """Process ERS tax payment"""
        return {
            "transaction_id": f"ERS_{''.join(secrets.choice(string.digits) for _ in range(10))}",
            "status": "completed",
            "amount_paid": payment_data['amount'],
            "taxpayer_id": payment_data['taxpayer_id'],
            "payment_type": payment_data.get('payment_type', 'income_tax'),
            "tax_year": payment_data.get('tax_year', '2024'),
            "receipt_number": f"TAX_{''.join(secrets.choice(string.digits) for _ in range(8))}",
            "payment_date": datetime.utcnow().isoformat(),
            "balance_remaining": max(0, payment_data.get('total_due', 0) - payment_data['amount'])
        }
    
    async def _process_fine_payment(self, payment_data: Dict) -> Dict:
        """Process police fine payment"""
        return {
            "transaction_id": f"POLICE_{''.join(secrets.choice(string.digits) for _ in range(10))}",
            "status": "completed",
            "amount_paid": payment_data['amount'],
            "fine_id": payment_data['fine_id'],
            "violation_type": payment_data.get('violation_type'),
            "receipt_number": f"FINE_{''.join(secrets.choice(string.digits) for _ in range(8))}",
            "payment_date": datetime.utcnow().isoformat(),
            "clearance_code": f"CLR_{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))}"
        }

class EducationServiceIntegration:
    """Handle education service payments (UNESWA, Schools)"""
    
    async def get_student_account(self, institution_code: str, student_id: str) -> Dict:
        """Get student account information"""
        if institution_code == "UNESWA":
            return await self._get_university_account(student_id)
        else:
            return await self._get_school_account(institution_code, student_id)
    
    async def _get_university_account(self, student_number: str) -> Dict:
        """Get UNESWA student account"""
        return {
            "student_number": student_number,
            "student_name": "Nomsa Dlamini",
            "faculty": "Faculty of Science and Engineering",
            "year_of_study": "Year 2",
            "current_semester": "Semester 2, 2024",
            "tuition_balance": 8500.00,
            "accommodation_balance": 2200.00,
            "meal_plan_balance": 1800.00,
            "library_fines": 25.00,
            "total_outstanding": 12525.00,
            "last_payment_date": "2024-07-20",
            "registration_status": "Registered",
            "financial_hold": False
        }
    
    async def _get_school_account(self, school_code: str, student_id: str) -> Dict:
        """Get school student account"""
        return {
            "student_id": student_id,
            "student_name": "Sipho Masilela",
            "school_name": "Mbabane High School",
            "grade": "Form 4",
            "class": "4A",
            "tuition_balance": 3200.00,
            "transport_balance": 450.00,
            "uniform_balance": 280.00,
            "examination_fees": 350.00,
            "total_outstanding": 4280.00,
            "term": "Term 3, 2024",
            "parent_name": "Maria Masilela",
            "parent_contact": "+268 7612 3456"
        }
    
    async def process_education_payment(self, payment_data: Dict) -> Dict:
        """Process education payment"""
        fee_type = payment_data.get('fee_type')
        
        return {
            "transaction_id": f"EDU_{''.join(secrets.choice(string.digits) for _ in range(10))}",
            "status": "completed",
            "amount_paid": payment_data['amount'],
            "student_id": payment_data['student_id'],
            "fee_type": fee_type,
            "academic_period": payment_data.get('academic_period'),
            "receipt_number": f"EDU_{''.join(secrets.choice(string.digits) for _ in range(8))}",
            "payment_date": datetime.utcnow().isoformat(),
            "balance_remaining": max(0, payment_data.get('current_balance', 0) - payment_data['amount']),
            "payment_reference": f"{fee_type.upper()} payment for {payment_data['student_id']}"
        }

class TransportServiceIntegration:
    """Handle transport service payments (EPTC)"""
    
    async def get_available_routes(self) -> List[Dict]:
        """Get available transport routes"""
        return [
            {"route_id": "R001", "route_name": "Mbabane - Manzini", "fare": 15.00, "duration": "45 mins"},
            {"route_id": "R002", "route_name": "Mbabane - Big Bend", "fare": 25.00, "duration": "90 mins"},
            {"route_id": "R003", "route_name": "Manzini - Siteki", "fare": 20.00, "duration": "75 mins"},
            {"route_id": "R004", "route_name": "Mbabane - Piggs Peak", "fare": 18.00, "duration": "60 mins"}
        ]
    
    async def purchase_transport_voucher(self, voucher_data: Dict) -> Dict:
        """Purchase transport voucher"""
        voucher_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        
        return {
            "transaction_id": f"EPTC_{''.join(secrets.choice(string.digits) for _ in range(10))}",
            "status": "completed",
            "voucher_code": voucher_code,
            "route_id": voucher_data['route_id'],
            "route_name": voucher_data['route_name'],
            "fare_paid": voucher_data['amount'],
            "valid_from": datetime.utcnow().isoformat(),
            "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "passenger_type": voucher_data.get('passenger_type', 'adult'),
            "qr_code_data": f"EPTC:{voucher_code}:{voucher_data['route_id']}",
            "receipt_number": f"EPTC_{''.join(secrets.choice(string.digits) for _ in range(8))}"
        }

class HospitalityServiceIntegration:
    """Handle hospitality service payments (Hotels, Restaurants)"""
    
    async def search_hotels(self, search_criteria: Dict) -> List[Dict]:
        """Search available hotels"""
        return [
            {
                "hotel_id": "HTL001",
                "hotel_name": "Esibayeni Lodge",
                "location": "Ezulwini Valley",
                "room_types": [
                    {"type": "Standard", "price": 850.00, "available": True},
                    {"type": "Deluxe", "price": 1200.00, "available": True},
                    {"type": "Suite", "price": 1800.00, "available": False}
                ],
                "amenities": ["WiFi", "Swimming Pool", "Restaurant", "Spa"],
                "rating": 4.5
            },
            {
                "hotel_id": "HTL002", 
                "hotel_name": "Mountain Inn",
                "location": "Mbabane",
                "room_types": [
                    {"type": "Standard", "price": 650.00, "available": True},
                    {"type": "Executive", "price": 950.00, "available": True}
                ],
                "amenities": ["WiFi", "Restaurant", "Conference Rooms"],
                "rating": 4.0
            }
        ]
    
    async def make_hotel_booking(self, booking_data: Dict) -> Dict:
        """Make hotel booking and process payment"""
        booking_reference = f"BK{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))}"
        
        return {
            "transaction_id": f"HTL_{''.join(secrets.choice(string.digits) for _ in range(10))}",
            "booking_reference": booking_reference,
            "status": "confirmed",
            "hotel_id": booking_data['hotel_id'],
            "hotel_name": booking_data['hotel_name'],
            "check_in": booking_data['check_in_date'],
            "check_out": booking_data['check_out_date'],
            "room_type": booking_data['room_type'],
            "guests": booking_data['number_of_guests'],
            "total_amount": booking_data['amount'],
            "payment_status": "completed",
            "confirmation_code": booking_reference,
            "cancellation_policy": "Free cancellation up to 24 hours before check-in"
        }
    
    async def process_restaurant_payment(self, payment_data: Dict) -> Dict:
        """Process restaurant payment"""
        return {
            "transaction_id": f"REST_{''.join(secrets.choice(string.digits) for _ in range(10))}",
            "status": "completed",
            "restaurant_name": payment_data['restaurant_name'],
            "table_number": payment_data.get('table_number'),
            "order_reference": payment_data.get('order_reference'),
            "amount_paid": payment_data['amount'],
            "tip_amount": payment_data.get('tip_amount', 0.00),
            "total_amount": payment_data['amount'] + payment_data.get('tip_amount', 0.00),
            "payment_date": datetime.utcnow().isoformat(),
            "receipt_number": f"REST_{''.join(secrets.choice(string.digits) for _ in range(8))}",
            "payment_method": "Fast Pay Digital"
        }

# Service Integration Factory
class ServiceIntegrationFactory:
    """Factory for creating service integration instances"""
    
    @staticmethod
    def get_integration(service_type: str):
        integrations = {
            'utility': UtilityServiceIntegration(),
            'government': GovernmentServiceIntegration(),
            'education': EducationServiceIntegration(),
            'transport': TransportServiceIntegration(),
            'hospitality': HospitalityServiceIntegration()
        }
        
        if service_type not in integrations:
            raise ValueError(f"Unsupported service type: {service_type}")
        
        return integrations[service_type]