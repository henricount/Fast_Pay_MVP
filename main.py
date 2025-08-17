from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.models.database import (
    get_db, init_db, Payment, Transaction, PaymentStatus, Merchant, QRCode
)
from app.models.schemas import (
    PaymentRequest, PaymentResponse, MerchantRegistration, MerchantResponse,
    QRCodeRequest, QRCodeResponse, PaymentInitiation
)
from app.services.api_gateway import APIGateway
from app.services.risk_engine import RiskEngine
from app.services.payment_orchestrator import PaymentOrchestrator
from app.services.merchant_service import MerchantService
from app.api.service_endpoints import router as service_router
from app.api.auth_endpoints import router as auth_router

# FastAPI App
app = FastAPI(
    title="Eswatini Payment System MVP",
    description="End-to-end payment processing demonstration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include service endpoints
app.include_router(service_router)
app.include_router(auth_router)

# Initialize services
api_gateway = APIGateway()
risk_engine = RiskEngine()
orchestrator = PaymentOrchestrator()
merchant_service = MerchantService()

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy", "service": "Fast Pay MVP"}

# Merchant Management Endpoints

@app.post("/api/v1/merchants/register", response_model=MerchantResponse)
async def register_merchant(
    registration: MerchantRegistration,
    db: Session = Depends(get_db)
):
    """Register a new merchant"""
    try:
        merchant = merchant_service.register_merchant(registration, db)
        
        return MerchantResponse(
            merchant_id=merchant.merchant_id,
            business_name=merchant.business_name,
            status=merchant.status.value,
            api_key=merchant.api_key,
            message=f"Merchant {merchant.business_name} registered successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/merchants/{merchant_id}")
async def get_merchant_details(merchant_id: str, db: Session = Depends(get_db)):
    """Get merchant details"""
    merchant = merchant_service.authenticate_merchant_id(merchant_id, db)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    return {
        "merchant_id": merchant.merchant_id,
        "business_name": merchant.business_name,
        "business_type": merchant.business_type.value,
        "owner_name": merchant.owner_name,
        "phone": merchant.phone,
        "email": merchant.email,
        "status": merchant.status.value,
        "fee_rate": merchant.fee_rate,
        "created_at": merchant.created_at
    }

@app.post("/api/v1/merchants/{merchant_id}/qr-codes", response_model=QRCodeResponse)
async def generate_qr_code(
    merchant_id: str,
    qr_request: QRCodeRequest,
    db: Session = Depends(get_db)
):
    """Generate QR code for merchant"""
    try:
        qr_code = merchant_service.generate_qr_code(merchant_id, qr_request, db)
        qr_data = merchant_service.generate_qr_data(qr_code)
        
        # Generate QR code image with URL encoding
        import urllib.parse
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?data={urllib.parse.quote(qr_data)}&size=200x200"
        
        return QRCodeResponse(
            qr_code_id=qr_code.qr_code_id,
            qr_code_data=qr_data,
            qr_code_url=qr_url,
            expires_at=qr_code.expires_at,
            is_dynamic=qr_code.is_dynamic
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/merchants/{merchant_id}/qr-codes")
async def get_merchant_qr_codes(merchant_id: str, db: Session = Depends(get_db)):
    """Get all QR codes for merchant"""
    qr_codes = merchant_service.get_merchant_qr_codes(merchant_id, db)
    
    return [
        {
            "qr_code_id": qr.qr_code_id,
            "amount": qr.amount,
            "description": qr.description,
            "is_dynamic": qr.is_dynamic,
            "expires_at": qr.expires_at,
            "usage_count": qr.usage_count,
            "max_usage": qr.max_usage,
            "is_active": qr.is_active,
            "created_at": qr.created_at
        }
        for qr in qr_codes
    ]

@app.post("/api/v1/payments/initiate", response_model=PaymentResponse)
async def initiate_payment(
    payment_initiation: PaymentInitiation,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Initiate payment via QR code or direct"""
    
    # If QR code provided, validate it
    if payment_initiation.qr_code_id:
        try:
            qr_code = merchant_service.validate_qr_code(payment_initiation.qr_code_id, db)
            
            # Use QR code amount if not provided
            if qr_code.amount and not payment_initiation.amount:
                payment_initiation.amount = qr_code.amount
                
            # Update usage count
            merchant_service.increment_qr_usage(payment_initiation.qr_code_id, db)
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Convert to standard payment request
    payment_request = PaymentRequest(
        merchant_id=payment_initiation.merchant_id,
        customer_id=payment_initiation.customer_id,
        amount=payment_initiation.amount,
        currency="SZL",
        payment_method=payment_initiation.payment_method,
        customer_location=None
    )
    
    # Process through normal payment pipeline
    return await create_payment(payment_request, background_tasks, db)

def log_transaction(db: Session, payment_id: str, step: str, status: str, details: dict):
    """Log each step of the payment process"""
    transaction = Transaction(
        payment_id=payment_id,
        step=step,
        status=status,
        details=json.dumps(details)
    )
    db.add(transaction)
    db.commit()

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")
        # Continue anyway for serverless environments

@app.post("/api/v1/payments", response_model=PaymentResponse)
async def create_payment(
    payment_request: PaymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Main payment processing endpoint"""

    # Step 1: API Gateway - Authentication & Rate Limiting
    if not api_gateway.authenticate_request(payment_request.merchant_id, db):
        raise HTTPException(status_code=401, detail="Invalid merchant credentials")

    if not api_gateway.check_rate_limit(payment_request.merchant_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Create payment record
    payment = Payment(
        merchant_id=payment_request.merchant_id,
        customer_id=payment_request.customer_id,
        amount=payment_request.amount,
        currency=payment_request.currency,
        status=PaymentStatus.PENDING
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    log_transaction(db, payment.id, "api_gateway", "success", {
        "message": "Payment request validated and accepted"
    })

    # Process payment asynchronously
    background_tasks.add_task(process_payment_pipeline, payment.id, payment_request)

    return PaymentResponse(
        payment_id=payment.id,
        status="pending",
        message="Payment initiated successfully",
        estimated_completion="2-5 seconds"
    )

async def process_payment_pipeline(payment_id: str, payment_request: PaymentRequest):
    """Background payment processing pipeline"""
    db = next(get_db())
    
    try:
        # Step 2: Risk Assessment
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        payment.status = PaymentStatus.RISK_CHECK
        db.commit()

        risk_assessment = await risk_engine.assess_risk(payment_request, payment_id)
        payment.risk_score = risk_assessment.risk_score

        log_transaction(db, payment_id, "risk_engine", "completed", {
            "risk_score": risk_assessment.risk_score,
            "risk_factors": risk_assessment.risk_factors,
            "recommendation": risk_assessment.recommendation
        })

        # Decline high-risk payments
        if risk_assessment.recommendation == "DECLINE":
            payment.status = PaymentStatus.FAILED
            payment.error_message = "Transaction declined due to high risk score"
            db.commit()
            log_transaction(db, payment_id, "risk_engine", "declined", {
                "reason": "High risk score",
                "risk_score": risk_assessment.risk_score
            })
            return

        # Step 3: Payment Orchestration
        payment.status = PaymentStatus.PROCESSING
        db.commit()

        settlement_rail = orchestrator.select_settlement_rail(payment_request, risk_assessment.risk_score)
        payment.settlement_rail = settlement_rail

        log_transaction(db, payment_id, "orchestrator", "routing", {
            "selected_rail": settlement_rail.value,
            "reason": f"Amount: {payment_request.amount}, Risk: {risk_assessment.risk_score}"
        })

        # Step 4: Settlement Processing
        settlement_result = await orchestrator.process_settlement(payment_request, settlement_rail)
        payment.settlement_response = json.dumps(settlement_result)

        if settlement_result["status"] == "completed":
            payment.status = PaymentStatus.COMPLETED
            payment.completed_at = datetime.utcnow()
            log_transaction(db, payment_id, "settlement", "completed", settlement_result)
        else:
            payment.status = PaymentStatus.FAILED
            payment.error_message = settlement_result.get("message", "Settlement failed")
            log_transaction(db, payment_id, "settlement", "failed", settlement_result)

        db.commit()

    except Exception as e:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        payment.status = PaymentStatus.FAILED
        payment.error_message = f"System error: {str(e)}"
        db.commit()

        log_transaction(db, payment_id, "system", "error", {
            "error": str(e)
        })
    finally:
        db.close()

@app.get("/api/v1/payments/{payment_id}")
async def get_payment_status(payment_id: str, db: Session = Depends(get_db)):
    """Get payment status and details"""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Get transaction log
    transactions = db.query(Transaction).filter(
        Transaction.payment_id == payment_id
    ).order_by(Transaction.timestamp).all()

    settlement_details = None
    if payment.settlement_response:
        settlement_details = json.loads(payment.settlement_response)

    return {
        "payment_id": payment.id,
        "status": payment.status.value,
        "amount": payment.amount,
        "currency": payment.currency,
        "risk_score": payment.risk_score,
        "settlement_rail": payment.settlement_rail.value if payment.settlement_rail else None,
        "settlement_details": settlement_details,
        "error_message": payment.error_message,
        "created_at": payment.created_at,
        "completed_at": payment.completed_at,
        "transaction_log": [
            {
                "step": t.step,
                "status": t.status,
                "timestamp": t.timestamp,
                "details": json.loads(t.details) if t.details else None
            }
            for t in transactions
        ]
    }

@app.get("/api/v1/analytics/dashboard")
async def get_analytics_dashboard(db: Session = Depends(get_db)):
    """Simple analytics dashboard"""

    # Get payment statistics
    total_payments = db.query(Payment).count()
    completed_payments = db.query(Payment).filter(Payment.status == PaymentStatus.COMPLETED).count()
    total_volume = db.query(Payment).filter(Payment.status == PaymentStatus.COMPLETED).all()
    total_amount = sum(p.amount for p in total_volume)

    # Settlement rail distribution
    from app.models.database import SettlementRail
    eswatini_payments = db.query(Payment).filter(
        Payment.settlement_rail == SettlementRail.ESWATINI_SWITCH
    ).count()
    visa_payments = db.query(Payment).filter(
        Payment.settlement_rail == SettlementRail.VISA_DIRECT
    ).count()

    # Risk score distribution
    high_risk = db.query(Payment).filter(Payment.risk_score > 0.7).count()
    medium_risk = db.query(Payment).filter(
        Payment.risk_score > 0.3, Payment.risk_score <= 0.7
    ).count()
    low_risk = db.query(Payment).filter(Payment.risk_score <= 0.3).count()

    return {
        "summary": {
            "total_payments": total_payments,
            "completed_payments": completed_payments,
            "success_rate": round(completed_payments / max(total_payments, 1) * 100, 1),
            "total_volume": round(total_amount, 2),
            "average_transaction": round(total_amount / max(completed_payments, 1), 2)
        },
        "settlement_distribution": {
            "eswatini_switch": eswatini_payments,
            "visa_direct": visa_payments
        },
        "risk_distribution": {
            "low_risk": low_risk,
            "medium_risk": medium_risk,
            "high_risk": high_risk
        }
    }

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def demo_frontend():
    """Serve the demo interface"""
    try:
        with open("app/static/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Fast Pay MVP</h1><p>Demo interface loading...</p>")

@app.get("/merchant", response_class=HTMLResponse)
async def merchant_dashboard():
    """Serve the merchant dashboard"""
    try:
        with open("app/static/merchant-dashboard.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Merchant Dashboard</h1><p>Dashboard loading...</p>")

@app.get("/services", response_class=HTMLResponse)
async def services_dashboard():
    """Serve the national services dashboard"""
    try:
        with open("app/static/services-dashboard.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Services Dashboard</h1><p>Dashboard loading...</p>")

@app.get("/auth", response_class=HTMLResponse)
async def authentication_page():
    """Serve the login/registration page"""
    try:
        with open("app/static/auth.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Authentication</h1><p>Login page loading...</p>")

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)