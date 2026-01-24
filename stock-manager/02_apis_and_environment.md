# 02. APIs & External Environment List

To operate effectively in the US market, a professional trading system requires high-fidelity data and reliable brokerage connectivity.

## 1. Primary Trading & Market Data APIs

| Category | Recommended API | Features |
| :--- | :--- | :--- |
| **Brokerage** | **Alpaca Markets** | Zero-commission, Paper-trading environment, Modern REST/Websocket API. |
| **High Fidelity Data** | **Polygon.io** | Low-latency tick-by-tick data, complete US market coverage. |
| **Fundamental Data** | **SEC EDGAR** | Direct access to 10-K, 10-Q filings for deep fundamental analysis. |
| **Alternative Data** | **Finnhub / NewsAPI** | Sentiment analysis, earnings transcripts, and social media trends. |
| **Legacy/Backup** | **Alpha Vantage** | Good for historical daily/monthly data (Already in .env). |

## 2. AI & Research APIs
- **Perplexity API**: Used for the AI Agent Chatbot to perform real-time web-searches and news summarization.
- **SEC-API.io**: Advanced parsing of SEC filings into JSON format (alternative to manual EDGAR parsing).

## 3. External Infrastructure (Deployment)

### Cloud Environment (AWS Recommended)
- **Compute**: **AWS EC2 (t3.medium or higher)** for running the backend 24/7.
- **Serverless**: **AWS Lambda** for scheduled tasks like daily portfolio rebalancing or morning news scanning.
- **Storage**: **AWS S3** for archiving historical trade logs and analysis reports.

### DevOps & Containers
- **Docker**: All services (Market, Strategy, Execution) should be containerized for environment consistency.
- **Docker Compose**: To orchestrate the Backend + Redis + Database locally or on VPS.
- **CI/CD**: GitHub Actions for automated testing and deployment.

## 4. Connectivity Requirements
- **Stable WebSocket**: Required for real-time price streaming (minimum 100Mbps stable link recommended for server).
- **Redundancy**: Dual data providers (e.g., Polygon + Finnhub) to prevent downtime during API outages.
