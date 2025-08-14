from sqlalchemy import Column, String, Enum, Boolean, DECIMAL, Text, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class ServiceType(enum.Enum):
    UTILITY = "utility"
    GOVERNMENT = "government"
    EDUCATION = "education"
    TRANSPORT = "transport"
    HOSPITALITY = "hospitality"
    FINANCIAL = "financial"

class ServiceSubCategory(enum.Enum):
    # Utilities
    WATER = "water"
    ELECTRICITY = "electricity"
    
    # Government
    TAX_PAYMENTS = "tax_payments"
    FINES = "fines"
    LICENSES = "licenses"
    PERMITS = "permits"
    
    # Education
    UNIVERSITY_FEES = "university_fees"
    SCHOOL_FEES = "school_fees"
    EXAMINATION_FEES = "examination_fees"
    ACCOMMODATION = "accommodation"
    
    # Transport
    PUBLIC_TRANSPORT = "public_transport"
    VOUCHERS = "vouchers"
    
    # Hospitality
    HOTEL_BOOKING = "hotel_booking"
    RESTAURANT_PAYMENT = "restaurant_payment"
    EVENT_BOOKING = "event_booking"
    
    # Financial
    CARD_SERVICES = "card_services"

class ServiceProvider(Base):
    __tablename__ = "service_providers"
    
    provider_id = Column(String(50), primary_key=True)
    provider_name = Column(String(200), nullable=False)
    provider_code = Column(String(20), unique=True, nullable=False)  # EWSC, EEC, etc.
    service_type = Column(Enum(ServiceType), nullable=False)
    subcategory = Column(Enum(ServiceSubCategory), nullable=False)
    
    # API Integration
    api_endpoint = Column(String(500))
    api_key_encrypted = Column(Text)
    webhook_url = Column(String(500))
    
    # Business Details
    contact_person = Column(String(100))
    contact_email = Column(String(100))
    contact_phone = Column(String(20))
    
    # Configuration
    is_active = Column(Boolean, default=True)
    requires_verification = Column(Boolean, default=False)
    min_amount = Column(DECIMAL(10, 2))
    max_amount = Column(DECIMAL(10, 2))
    processing_fee_percent = Column(DECIMAL(5, 4), default=0.015)  # 1.5%
    processing_fee_fixed = Column(DECIMAL(10, 2), default=0.00)
    
    # Metadata
    service_config = Column(JSON)  # Service-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    service_categories = relationship("ServiceCategory", back_populates="provider")
    transactions = relationship("ServiceTransaction", back_populates="provider")

class ServiceCategory(Base):
    __tablename__ = "service_categories"
    
    category_id = Column(String(50), primary_key=True)
    provider_id = Column(String(50), ForeignKey("service_providers.provider_id"), nullable=False)
    category_name = Column(String(200), nullable=False)
    category_code = Column(String(50), nullable=False)  # WATER_BILL, ELECTRICITY_PREPAID
    category_description = Column(Text)
    
    # Billing Configuration
    billing_cycle = Column(String(20))  # monthly, prepaid, one-time
    supports_autopay = Column(Boolean, default=False)
    requires_customer_id = Column(Boolean, default=True)
    customer_id_format = Column(String(100))  # Regex pattern for validation
    
    # Amount Limits
    min_amount = Column(DECIMAL(10, 2))
    max_amount = Column(DECIMAL(10, 2))
    
    # Processing
    processing_time_minutes = Column(Integer, default=5)
    confirmation_required = Column(Boolean, default=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    provider = relationship("ServiceProvider", back_populates="service_categories")

class ServiceTransaction(Base):
    __tablename__ = "service_transactions"
    
    transaction_id = Column(String(50), primary_key=True)
    provider_id = Column(String(50), ForeignKey("service_providers.provider_id"), nullable=False)
    category_id = Column(String(50), ForeignKey("service_categories.category_id"), nullable=False)
    
    # Customer Information
    customer_id = Column(String(50), nullable=False)  # Fast Pay customer
    service_customer_id = Column(String(100), nullable=False)  # Provider's customer ID
    customer_name = Column(String(200))
    
    # Transaction Details
    amount = Column(DECIMAL(12, 2), nullable=False)
    processing_fee = Column(DECIMAL(10, 2), default=0.00)
    total_amount = Column(DECIMAL(12, 2), nullable=False)
    currency = Column(String(3), default="SZL")
    
    # Transaction Status
    status = Column(String(20), default="pending")  # pending, processing, completed, failed, cancelled
    provider_reference = Column(String(100))  # Provider's transaction reference
    provider_response = Column(JSON)  # Full provider response
    
    # Metadata
    description = Column(Text)
    service_metadata = Column(JSON)  # Service-specific data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    provider = relationship("ServiceProvider", back_populates="transactions")

# Specific Service Models

class UtilityBilling(Base):
    __tablename__ = "utility_billing"
    
    billing_id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), nullable=False)
    provider_id = Column(String(50), ForeignKey("service_providers.provider_id"))
    
    # Account Information
    utility_account_number = Column(String(50), nullable=False)
    meter_number = Column(String(50))
    account_holder_name = Column(String(200))
    
    # Billing Details
    current_balance = Column(DECIMAL(12, 2))
    last_reading = Column(DECIMAL(10, 2))
    current_reading = Column(DECIMAL(10, 2))
    billing_period_start = Column(DateTime)
    billing_period_end = Column(DateTime)
    
    # Configuration
    auto_pay_enabled = Column(Boolean, default=False)
    auto_pay_threshold = Column(DECIMAL(10, 2))
    low_balance_alert = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EducationPayment(Base):
    __tablename__ = "education_payments"
    
    payment_id = Column(String(50), primary_key=True)
    institution_id = Column(String(50), ForeignKey("service_providers.provider_id"))
    student_id = Column(String(50), nullable=False)
    
    # Student Information
    student_name = Column(String(200), nullable=False)
    student_number = Column(String(50), nullable=False)
    grade_level = Column(String(20))  # Grade 1-12, University Year 1-4
    class_section = Column(String(50))
    
    # Payment Details
    fee_type = Column(String(50), nullable=False)  # tuition, accommodation, meals, transport
    academic_year = Column(String(20))
    semester_term = Column(String(20))
    
    # Parent/Guardian Information
    parent_name = Column(String(200))
    parent_phone = Column(String(20))
    parent_email = Column(String(100))
    
    # Payment Plan
    total_amount = Column(DECIMAL(12, 2))
    amount_paid = Column(DECIMAL(12, 2), default=0.00)
    balance_due = Column(DECIMAL(12, 2))
    due_date = Column(DateTime)
    
    # Status
    payment_status = Column(String(20), default="pending")
    is_overdue = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class HospitalityService(Base):
    __tablename__ = "hospitality_services"
    
    service_id = Column(String(50), primary_key=True)
    provider_id = Column(String(50), ForeignKey("service_providers.provider_id"))
    customer_id = Column(String(50), nullable=False)
    
    # Service Details
    service_type = Column(String(50), nullable=False)  # hotel_booking, restaurant_payment
    booking_reference = Column(String(100))
    
    # Hotel/Restaurant Information
    establishment_name = Column(String(200))
    location = Column(String(200))
    contact_info = Column(JSON)
    
    # Booking Details (for hotels)
    check_in_date = Column(DateTime)
    check_out_date = Column(DateTime)
    room_type = Column(String(100))
    number_of_guests = Column(Integer)
    
    # Service Details (for restaurants)
    table_number = Column(String(20))
    order_details = Column(JSON)
    special_requests = Column(Text)
    
    # Payment
    base_amount = Column(DECIMAL(12, 2))
    taxes_fees = Column(DECIMAL(10, 2))
    total_amount = Column(DECIMAL(12, 2))
    
    # Status
    booking_status = Column(String(20), default="confirmed")
    payment_status = Column(String(20), default="pending")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VisaCard(Base):
    __tablename__ = "visa_cards"
    
    card_id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), nullable=False)
    
    # Card Details
    card_number_encrypted = Column(Text, nullable=False)
    card_type = Column(String(20), default="prepaid")  # prepaid, debit, credit
    card_variant = Column(String(20), default="physical")  # physical, virtual, youth, corporate
    
    # Card Information
    cardholder_name = Column(String(200), nullable=False)
    expiry_date = Column(String(7))  # MM/YYYY format
    cvv_encrypted = Column(Text)
    
    # Financial Details
    balance = Column(DECIMAL(12, 2), default=0.00)
    available_balance = Column(DECIMAL(12, 2), default=0.00)
    daily_limit = Column(DECIMAL(10, 2), default=5000.00)
    monthly_limit = Column(DECIMAL(12, 2), default=50000.00)
    international_enabled = Column(Boolean, default=False)
    
    # Status
    status = Column(String(20), default="active")  # active, blocked, expired, cancelled
    pin_set = Column(Boolean, default=False)
    
    # Metadata
    issued_date = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    activation_date = Column(DateTime)
    
    # Tracking
    total_transactions = Column(Integer, default=0)
    total_spent = Column(DECIMAL(12, 2), default=0.00)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CardTransaction(Base):
    __tablename__ = "card_transactions"
    
    transaction_id = Column(String(50), primary_key=True)
    card_id = Column(String(50), ForeignKey("visa_cards.card_id"), nullable=False)
    
    # Transaction Details
    transaction_type = Column(String(30), nullable=False)  # purchase, withdrawal, refund, top_up
    amount = Column(DECIMAL(12, 2), nullable=False)
    currency = Column(String(3), default="SZL")
    exchange_rate = Column(DECIMAL(10, 6))
    
    # Merchant Information
    merchant_name = Column(String(200))
    merchant_category = Column(String(100))
    merchant_location = Column(String(200))
    merchant_country = Column(String(50))
    
    # Processing
    authorization_code = Column(String(50))
    reference_number = Column(String(100))
    status = Column(String(20), default="pending")  # pending, approved, declined, reversed
    
    # Security
    is_international = Column(Boolean, default=False)
    risk_score = Column(DECIMAL(3, 2))
    
    # Timestamps
    transaction_date = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)