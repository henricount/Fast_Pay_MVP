from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.database import get_db
from app.services.service_integration import ServiceIntegrationFactory
from app.services.visa_card_service import VisaCardService

router = APIRouter(prefix="/api/v1/services", tags=["services"])
visa_service = VisaCardService()

# Pydantic Models for Service Requests

class UtilityInquiryRequest(BaseModel):
    provider_code: str = Field(..., example="EWSC")
    account_number: str = Field(..., example="123456789")

class UtilityPaymentRequest(BaseModel):
    provider_code: str = Field(..., example="EWSC")
    account_number: str = Field(..., example="123456789")
    amount: float = Field(..., gt=0, example=450.75)
    customer_id: str = Field(..., example="CUST_001")

class GovernmentInquiryRequest(BaseModel):
    service_type: str = Field(..., example="tax_payment")
    identifier: str = Field(..., example="taxpayer_id_or_id_number")

class GovernmentPaymentRequest(BaseModel):
    service_type: str = Field(..., example="tax_payment")
    identifier: str = Field(..., example="taxpayer_id")
    amount: float = Field(..., gt=0, example=2500.00)
    customer_id: str = Field(..., example="CUST_001")
    reference_id: Optional[str] = Field(None, example="FINE_2024_001234")

class EducationInquiryRequest(BaseModel):
    institution_code: str = Field(..., example="UNESWA")
    student_id: str = Field(..., example="202012345")

class EducationPaymentRequest(BaseModel):
    institution_code: str = Field(..., example="UNESWA")
    student_id: str = Field(..., example="202012345")
    fee_type: str = Field(..., example="tuition")
    amount: float = Field(..., gt=0, example=8500.00)
    customer_id: str = Field(..., example="CUST_001")

class TransportVoucherRequest(BaseModel):
    route_id: str = Field(..., example="R001")
    passenger_type: str = Field(default="adult", example="adult")
    quantity: int = Field(default=1, example=1)
    customer_id: str = Field(..., example="CUST_001")

class HotelSearchRequest(BaseModel):
    check_in_date: str = Field(..., example="2024-09-01")
    check_out_date: str = Field(..., example="2024-09-03")
    location: Optional[str] = Field(None, example="Ezulwini Valley")
    guests: int = Field(default=1, example=2)

class HotelBookingRequest(BaseModel):
    hotel_id: str = Field(..., example="HTL001")
    room_type: str = Field(..., example="Standard")
    check_in_date: str = Field(..., example="2024-09-01")
    check_out_date: str = Field(..., example="2024-09-03")
    number_of_guests: int = Field(..., example=2)
    guest_name: str = Field(..., example="John Dlamini")
    amount: float = Field(..., gt=0, example=1700.00)
    customer_id: str = Field(..., example="CUST_001")

class RestaurantPaymentRequest(BaseModel):
    restaurant_name: str = Field(..., example="Malandela's Restaurant")
    table_number: Optional[str] = Field(None, example="T12")
    order_reference: Optional[str] = Field(None, example="ORD123456")
    amount: float = Field(..., gt=0, example=285.50)
    tip_amount: Optional[float] = Field(0.00, example=42.50)
    customer_id: str = Field(..., example="CUST_001")

class VisaCardRequest(BaseModel):
    cardholder_name: str = Field(..., example="John Dlamini")
    card_variant: str = Field(default="physical", example="physical")
    international_enabled: bool = Field(default=False, example=False)

class CardTopUpRequest(BaseModel):
    card_id: str = Field(..., example="CARD_ABC12345")
    amount: float = Field(..., gt=0, example=500.00)

class CardTransactionRequest(BaseModel):
    card_id: str = Field(..., example="CARD_ABC12345")
    amount: float = Field(..., gt=0, example=125.50)
    merchant_name: str = Field(..., example="SuperSpar Mbabane")
    merchant_category: Optional[str] = Field(None, example="grocery")
    merchant_location: Optional[str] = Field(None, example="Mbabane")
    merchant_country: str = Field(default="Eswatini", example="Eswatini")
    transaction_type: str = Field(default="purchase", example="purchase")

# Utility Service Endpoints

@router.get("/utilities/balance")
async def get_utility_balance(
    provider_code: str,
    account_number: str,
    db: Session = Depends(get_db)
):
    """Get utility account balance (Water/Electricity)"""
    try:
        integration = ServiceIntegrationFactory.get_integration('utility')
        balance_info = await integration.get_customer_balance(provider_code, account_number)
        return {"status": "success", "data": balance_info}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Service temporarily unavailable")

@router.post("/utilities/payment")
async def pay_utility_bill(
    payment_request: UtilityPaymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Pay utility bill (Water/Electricity)"""
    try:
        integration = ServiceIntegrationFactory.get_integration('utility')
        
        # Get current balance first
        balance_info = await integration.get_customer_balance(
            payment_request.provider_code, 
            payment_request.account_number
        )
        
        # Process payment
        payment_data = {
            'provider_code': payment_request.provider_code,
            'account_number': payment_request.account_number,
            'amount': payment_request.amount,
            'customer_id': payment_request.customer_id,
            'current_balance': balance_info.get('current_balance', 0)
        }
        
        result = await integration.process_utility_payment(payment_data)
        return {"status": "success", "data": result}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Payment processing failed")

# Government Service Endpoints

@router.get("/government/liability")
async def get_government_liability(
    service_type: str,
    identifier: str,
    db: Session = Depends(get_db)
):
    """Get government service liability (Tax/Fines)"""
    try:
        integration = ServiceIntegrationFactory.get_integration('government')
        
        if service_type == "tax_payment":
            liability_info = await integration.get_tax_liability(identifier)
        elif service_type == "fine_payment":
            liability_info = await integration.get_police_fines(identifier)
        else:
            raise ValueError(f"Unsupported service type: {service_type}")
            
        return {"status": "success", "data": liability_info}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Service temporarily unavailable")

@router.post("/government/payment")
async def pay_government_service(
    payment_request: GovernmentPaymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Pay government service (Tax/Fines/Licenses)"""
    try:
        integration = ServiceIntegrationFactory.get_integration('government')
        
        payment_data = {
            'service_type': payment_request.service_type,
            'identifier': payment_request.identifier,
            'amount': payment_request.amount,
            'customer_id': payment_request.customer_id,
            'reference_id': payment_request.reference_id
        }
        
        if payment_request.service_type == "fine_payment":
            payment_data['fine_id'] = payment_request.reference_id
        elif payment_request.service_type == "tax_payment":
            payment_data['taxpayer_id'] = payment_request.identifier
            
        result = await integration.process_government_payment(payment_data)
        return {"status": "success", "data": result}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Payment processing failed")

# Education Service Endpoints

@router.get("/education/account")
async def get_student_account(
    institution_code: str,
    student_id: str,
    db: Session = Depends(get_db)
):
    """Get student account information"""
    try:
        integration = ServiceIntegrationFactory.get_integration('education')
        account_info = await integration.get_student_account(institution_code, student_id)
        return {"status": "success", "data": account_info}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Service temporarily unavailable")

@router.post("/education/payment")
async def pay_education_fees(
    payment_request: EducationPaymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Pay education fees (School/University)"""
    try:
        integration = ServiceIntegrationFactory.get_integration('education')
        
        # Get student account first
        account_info = await integration.get_student_account(
            payment_request.institution_code,
            payment_request.student_id
        )
        
        payment_data = {
            'institution_code': payment_request.institution_code,
            'student_id': payment_request.student_id,
            'fee_type': payment_request.fee_type,
            'amount': payment_request.amount,
            'customer_id': payment_request.customer_id,
            'current_balance': account_info.get('total_outstanding', 0)
        }
        
        result = await integration.process_education_payment(payment_data)
        return {"status": "success", "data": result}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Payment processing failed")

# Transport Service Endpoints

@router.get("/transport/routes")
async def get_transport_routes(db: Session = Depends(get_db)):
    """Get available transport routes"""
    try:
        integration = ServiceIntegrationFactory.get_integration('transport')
        routes = await integration.get_available_routes()
        return {"status": "success", "data": routes}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Service temporarily unavailable")

@router.post("/transport/voucher")
async def purchase_transport_voucher(
    voucher_request: TransportVoucherRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Purchase transport voucher"""
    try:
        integration = ServiceIntegrationFactory.get_integration('transport')
        
        # Get routes to find fare
        routes = await integration.get_available_routes()
        selected_route = next((r for r in routes if r['route_id'] == voucher_request.route_id), None)
        
        if not selected_route:
            raise ValueError("Invalid route selected")
        
        voucher_data = {
            'route_id': voucher_request.route_id,
            'route_name': selected_route['route_name'],
            'amount': selected_route['fare'] * voucher_request.quantity,
            'passenger_type': voucher_request.passenger_type,
            'quantity': voucher_request.quantity,
            'customer_id': voucher_request.customer_id
        }
        
        result = await integration.purchase_transport_voucher(voucher_data)
        return {"status": "success", "data": result}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Voucher purchase failed")

# Hospitality Service Endpoints

@router.get("/hospitality/hotels")
async def search_hotels(
    check_in: str,
    check_out: str,
    location: Optional[str] = None,
    guests: int = 1,
    db: Session = Depends(get_db)
):
    """Search available hotels"""
    try:
        integration = ServiceIntegrationFactory.get_integration('hospitality')
        search_criteria = {
            'check_in_date': check_in,
            'check_out_date': check_out,
            'location': location,
            'guests': guests
        }
        hotels = await integration.search_hotels(search_criteria)
        return {"status": "success", "data": hotels}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Hotel search temporarily unavailable")

@router.post("/hospitality/hotel/booking")
async def make_hotel_booking(
    booking_request: HotelBookingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Make hotel booking and process payment"""
    try:
        integration = ServiceIntegrationFactory.get_integration('hospitality')
        
        booking_data = {
            'hotel_id': booking_request.hotel_id,
            'hotel_name': f"Hotel {booking_request.hotel_id}",  # Would be fetched from hotel search
            'room_type': booking_request.room_type,
            'check_in_date': booking_request.check_in_date,
            'check_out_date': booking_request.check_out_date,
            'number_of_guests': booking_request.number_of_guests,
            'guest_name': booking_request.guest_name,
            'amount': booking_request.amount,
            'customer_id': booking_request.customer_id
        }
        
        result = await integration.make_hotel_booking(booking_data)
        return {"status": "success", "data": result}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Booking failed")

@router.post("/hospitality/restaurant/payment")
async def pay_restaurant_bill(
    payment_request: RestaurantPaymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process restaurant payment"""
    try:
        integration = ServiceIntegrationFactory.get_integration('hospitality')
        
        payment_data = {
            'restaurant_name': payment_request.restaurant_name,
            'table_number': payment_request.table_number,
            'order_reference': payment_request.order_reference,
            'amount': payment_request.amount,
            'tip_amount': payment_request.tip_amount,
            'customer_id': payment_request.customer_id
        }
        
        result = await integration.process_restaurant_payment(payment_data)
        return {"status": "success", "data": result}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Payment processing failed")

# Visa Card Service Endpoints

@router.post("/cards/visa/issue")
async def issue_visa_card(
    card_request: VisaCardRequest,
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Issue a new Visa prepaid card"""
    try:
        card_data = {
            'cardholder_name': card_request.cardholder_name,
            'card_variant': card_request.card_variant,
            'international_enabled': card_request.international_enabled
        }
        
        result = visa_service.issue_card(customer_id, card_data, db)
        return {"status": "success", "data": result}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Card issuance failed")

@router.post("/cards/visa/topup")
async def top_up_visa_card(
    topup_request: CardTopUpRequest,
    db: Session = Depends(get_db)
):
    """Load money onto Visa prepaid card"""
    try:
        result = visa_service.load_card_balance(
            topup_request.card_id,
            topup_request.amount,
            db
        )
        return {"status": "success", "data": result}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Card top-up failed")

@router.get("/cards/visa/{card_id}")
async def get_visa_card_details(card_id: str, db: Session = Depends(get_db)):
    """Get Visa card details"""
    try:
        card_details = visa_service.get_card_details(card_id, db)
        return {"status": "success", "data": card_details}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unable to retrieve card details")

@router.get("/cards/visa/{card_id}/transactions")
async def get_card_transactions(
    card_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get Visa card transaction history"""
    try:
        transactions = visa_service.get_card_transactions(card_id, limit, db)
        return {"status": "success", "data": transactions}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unable to retrieve transactions")

@router.post("/cards/visa/transaction")
async def process_card_transaction(
    transaction_request: CardTransactionRequest,
    db: Session = Depends(get_db)
):
    """Process Visa card transaction"""
    try:
        transaction_data = {
            'card_id': transaction_request.card_id,
            'amount': transaction_request.amount,
            'merchant_name': transaction_request.merchant_name,
            'merchant_category': transaction_request.merchant_category,
            'merchant_location': transaction_request.merchant_location,
            'merchant_country': transaction_request.merchant_country,
            'transaction_type': transaction_request.transaction_type
        }
        
        result = visa_service.process_card_transaction(transaction_data, db)
        return {"status": "success", "data": result}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Transaction processing failed")

@router.post("/cards/visa/{card_id}/block")
async def block_visa_card(
    card_id: str,
    reason: str,
    db: Session = Depends(get_db)
):
    """Block a Visa card"""
    try:
        result = visa_service.block_card(card_id, reason, db)
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unable to block card")

@router.post("/cards/visa/{card_id}/unblock")
async def unblock_visa_card(card_id: str, db: Session = Depends(get_db)):
    """Unblock a Visa card"""
    try:
        result = visa_service.unblock_card(card_id, db)
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unable to unblock card")

# Service Provider Management (Admin endpoints)

@router.get("/providers")
async def list_service_providers(db: Session = Depends(get_db)):
    """List all available service providers"""
    # This would return all registered service providers
    return {
        "status": "success",
        "data": {
            "utilities": ["EWSC - Eswatini Water Services", "EEC - Eswatini Electricity"],
            "government": ["ERS - Revenue Services", "POLICE - Police Services"],
            "education": ["UNESWA - University of Eswatini", "SCHOOLS - Primary/Secondary"],
            "transport": ["EPTC - Public Transport Corporation"],
            "hospitality": ["HOTELS - Hotel Bookings", "RESTAURANTS - Restaurant Payments"]
        }
    }

@router.get("/health")
async def service_health_check():
    """Health check for all services"""
    return {
        "status": "healthy",
        "services": {
            "utilities": "operational",
            "government": "operational", 
            "education": "operational",
            "transport": "operational",
            "hospitality": "operational",
            "visa_cards": "operational"
        },
        "timestamp": datetime.now().isoformat()
    }