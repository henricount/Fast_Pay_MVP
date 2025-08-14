# Fast Pay MVP - Eswatini Payment System

A comprehensive fintech MVP demonstrating end-to-end payment processing with risk assessment, smart routing, and multi-rail settlement capabilities.

## 🚀 Features

- **API Gateway**: Authentication, rate limiting, request validation
- **Risk Engine**: ML-based fraud detection and risk scoring
- **Payment Orchestration**: Smart routing based on amount, currency, and risk
- **Multi-Rail Settlement**: 
  - Eswatini National Payment Switch (local, low-cost)
  - Visa Direct (international, higher coverage)
- **Real-time Analytics**: Transaction monitoring and business intelligence
- **Demo Interface**: Interactive web UI for testing

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │───▶│  Risk Engine    │───▶│  Orchestrator   │
│                 │    │                 │    │                 │
│ • Auth          │    │ • ML Models     │    │ • Smart Routing │
│ • Rate Limiting │    │ • Fraud Det.    │    │ • Settlement    │
│ • Validation    │    │ • Risk Scoring  │    │ • Multi-Rail    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                              ┌─────────────────┐
                                              │   Settlement    │
                                              │                 │
                                              │ • Eswatini SW   │
                                              │ • Visa Direct   │
                                              └─────────────────┘
```

## 🛠️ Quick Start

### Option 1: Simple Start (Recommended)

```bash
# Clone and navigate to project
cd Fast_Pay

# Run the startup script
./start.sh
```

The script will:
- Create a virtual environment
- Install dependencies
- Initialize the database
- Start the server on http://localhost:8000

### Option 2: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the application
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Docker

```bash
# Build and run with Docker
docker-compose up --build

# Or for production with nginx
docker-compose --profile production up --build
```

## 📱 Usage

### Demo Interface
Visit http://localhost:8000 for the interactive demo interface.

### API Endpoints

**Process Payment:**
```bash
curl -X POST "http://localhost:8000/api/v1/payments" \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "MERCH_001",
    "customer_id": "CUST_001", 
    "amount": 1000.0,
    "currency": "SZL",
    "payment_method": "qr_code",
    "customer_location": "Manzini"
  }'
```

**Check Payment Status:**
```bash
curl "http://localhost:8000/api/v1/payments/{payment_id}"
```

**Analytics Dashboard:**
```bash
curl "http://localhost:8000/api/v1/analytics/dashboard"
```

**API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test
pytest tests/test_api.py::test_create_payment
```

## 📊 Payment Flow

1. **Request Validation** - API Gateway validates merchant credentials and rate limits
2. **Risk Assessment** - ML models analyze transaction for fraud patterns
3. **Smart Routing** - Orchestrator selects optimal settlement rail
4. **Settlement** - Process through Eswatini Switch or Visa Direct
5. **Confirmation** - Real-time status updates and analytics

## 💰 Settlement Rails

### Eswatini National Payment Switch
- **Use Case**: Local SZL transactions ≤ 10,000 SZL
- **Fee**: 1.5%
- **Settlement**: T+0 (same day)
- **Success Rate**: 95%

### Visa Direct
- **Use Case**: International transactions, high amounts, high-risk
- **Fee**: 2.5%
- **Settlement**: T+1 (next day)
- **Success Rate**: 92%

## ⚙️ Configuration

Environment variables (optional):

```bash
# Database
DATABASE_URL=sqlite:///./payments.db

# API Settings  
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Rate Limiting
RATE_LIMIT_PER_MINUTE=10

# Risk Engine
HIGH_AMOUNT_THRESHOLD=5000
MAX_DAILY_AMOUNT=50000

# Settlement Rails
ESW_MAX_AMOUNT=10000
ESW_FEE_RATE=0.015
VISA_FEE_RATE=0.025
```

## 📁 Project Structure

```
Fast_Pay/
├── app/
│   ├── models/          # Database models and schemas
│   ├── services/        # Business logic (API Gateway, Risk Engine, etc.)
│   └── static/          # Frontend assets
├── tests/               # Test suite
├── main.py             # FastAPI application entry point
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── Dockerfile         # Container definition
├── docker-compose.yml # Multi-container setup
└── start.sh           # Quick start script
```

## 🔒 Security Features

- Merchant authentication
- Rate limiting (10 requests/minute)
- Risk-based transaction blocking
- SQL injection protection
- CORS policy management

## 📈 Monitoring & Analytics

The system provides real-time insights on:
- Transaction volume and success rates
- Settlement rail distribution
- Risk score distributions
- Payment status tracking
- Error analysis

## 🚀 Deployment

**Quick Deploy Options:**

1. **Railway (Recommended)**: [Deploy to Railway](https://railway.app) - Best for FastAPI
2. **Render**: [Deploy to Render](https://render.com) - Great free tier
3. **Vercel**: Limited serverless support
4. **Docker**: Works anywhere

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

## 🚧 Production Considerations

For production deployment:

1. **Database**: Replace SQLite with PostgreSQL/MySQL
2. **Security**: Implement proper API key management
3. **Monitoring**: Add logging, metrics, and alerting
4. **Scaling**: Use load balancers and container orchestration
5. **Compliance**: Implement PCI DSS requirements

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

This is a demonstration MVP for educational purposes.

---

Built with ❤️ for the Eswatini fintech ecosystem