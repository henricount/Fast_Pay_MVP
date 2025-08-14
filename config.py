import os
from typing import Dict, Any

class Config:
    """Application configuration"""
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./payments.db")
    
    # API Settings
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    API_KEY_HEADER = "X-API-Key"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    
    # Risk Engine Settings
    RISK_CONFIG = {
        "high_amount_threshold": float(os.getenv("HIGH_AMOUNT_THRESHOLD", "5000")),
        "unusual_hours": [0, 1, 2, 3, 4, 5],  # Late night transactions
        "high_frequency_minutes": int(os.getenv("HIGH_FREQ_MINUTES", "5")),
        "max_daily_amount": float(os.getenv("MAX_DAILY_AMOUNT", "50000"))
    }
    
    # Settlement Rails
    SETTLEMENT_CONFIG = {
        "eswatini_switch": {
            "max_amount": float(os.getenv("ESW_MAX_AMOUNT", "10000")),
            "currencies": ["SZL"],
            "fee_rate": float(os.getenv("ESW_FEE_RATE", "0.015")),
            "success_rate": float(os.getenv("ESW_SUCCESS_RATE", "0.95"))
        },
        "visa_direct": {
            "max_amount": float(os.getenv("VISA_MAX_AMOUNT", "100000")),
            "currencies": ["SZL", "USD", "EUR"],
            "fee_rate": float(os.getenv("VISA_FEE_RATE", "0.025")),
            "success_rate": float(os.getenv("VISA_SUCCESS_RATE", "0.92"))
        }
    }

# Global config instance
config = Config()