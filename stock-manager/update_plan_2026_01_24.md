# PM-MCP Stock-Manager 빌드 플랜
> **작성일**: 2026-01-24
> **버전**: 3.0 (개인용 최적화)
> **상태**: 빌드 준비 완료

---

## 🎯 프로젝트 목표

**개인용 미국 주식 자동매매 시스템 구축**
- PM-MCP의 분석 엔진을 활용한 자동매매
- 실시간 포지션 모니터링 대시보드
- AI 기반 종목 리서치 챗봇
- 로컬 환경에서 24/7 자동 실행

---

## 📐 간소화된 시스템 아키텍처

### 전체 구조
```
┌─────────────────────────────────────────────────┐
│  Frontend (React + Vite)                        │
│  - 포지션 모니터링 대시보드                      │
│  - 매매 내역 및 성과 분석                        │
│  - AI 챗봇 사이드바                              │
│  - Recharts 차트                                 │
└─────────────────────────────────────────────────┘
                      ▲
                      │ REST API / SSE
                      ▼
┌─────────────────────────────────────────────────┐
│  Backend (FastAPI - 단일 앱)                     │
│  ┌──────────────────────────────────────────┐   │
│  │  PM-MCP Integration Layer                │   │
│  │  ✓ ranking_advanced()     - 종목 선정    │   │
│  │  ✓ portfolio_evaluate()   - 포트폴리오   │   │
│  │  ✓ news_sentiment()       - 감성 분석    │   │
│  │  ✓ market_get_prices()    - 시장 데이터  │   │
│  │  ✓ scheduler              - 자동 실행    │   │
│  │  ✓ cache_manager          - 캐싱        │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  Trading Engine (신규 구현)               │   │
│  │  • broker.py      - Alpaca API 연동      │   │
│  │  • strategy.py    - 매매 전략 로직       │   │
│  │  • monitor.py     - 실시간 포지션 추적   │   │
│  │  • backtest.py    - 백테스팅            │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│  Database (SQLite)                              │
│  - trades (매매 내역)                            │
│  - positions (현재 포지션)                       │
│  - orders (주문 내역)                            │
│  - performance (성과 추적)                       │
└─────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│  External APIs (무료 중심)                       │
│  ✓ Alpaca Markets (Paper Trading - 무료)        │
│  ✓ Yahoo Finance (시장 데이터 - 무료)           │
│  ✓ Alpha Vantage (기술 지표 - 무료 tier)        │
│  ✓ Finnhub (뉴스/펀더멘털 - 무료 tier)          │
│  ✓ Perplexity API (AI 챗봇 - 기존)             │
└─────────────────────────────────────────────────┘
```

---

## 🔧 기술 스택 (간소화)

### Frontend
- **Framework**: React 18 + Vite
- **Styling**: Tailwind CSS
- **Charts**: Recharts (경량, 간단)
- **State**: React Query + Zustand
- **실시간**: EventSource (SSE)

### Backend
- **Framework**: FastAPI (Python 3.12+)
- **Task Scheduler**: APScheduler (PM-MCP 기존)
- **Async**: asyncio
- **ORM**: SQLAlchemy

### Database
- **Primary**: SQLite (개발/개인용)
- **Optional**: PostgreSQL (확장 시)
- **Cache**: diskcache (PM-MCP 기존)

### APIs
- **Broker**: Alpaca Markets (무료 Paper Trading)
- **Data**: Yahoo Finance, Alpha Vantage, Finnhub
- **AI**: Perplexity API

### Deployment
- **로컬 실행**: uvicorn + PM2
- **백그라운드**: systemd 또는 PM2
- **Optional**: Docker Compose

---

## 📁 프로젝트 구조

```
stock-manager/
├── backend/
│   ├── main.py                      # FastAPI 앱 진입점
│   ├── config.py                    # 설정 (API 키, DB 경로)
│   ├── database.py                  # SQLite 설정
│   │
│   ├── api/                         # REST API 엔드포인트
│   │   ├── trading.py               # 매매 관련 API
│   │   ├── monitoring.py            # 실시간 모니터링 SSE
│   │   ├── portfolio.py             # 포트폴리오 조회
│   │   └── chatbot.py               # AI 챗봇 프록시
│   │
│   ├── services/                    # 비즈니스 로직
│   │   ├── pm_mcp_integration.py    # PM-MCP 함수 Import
│   │   ├── broker_alpaca.py         # Alpaca API 래퍼
│   │   ├── strategy_engine.py       # 매매 전략 로직
│   │   ├── position_monitor.py      # 포지션 실시간 추적
│   │   └── backtest_engine.py       # 백테스팅
│   │
│   ├── models/                      # SQLAlchemy 모델
│   │   ├── trade.py
│   │   ├── position.py
│   │   ├── order.py
│   │   └── performance.py
│   │
│   ├── scheduler/                   # 스케줄 작업
│   │   └── trading_tasks.py         # 자동매매 작업
│   │
│   └── utils/                       # 유틸리티
│       ├── logger.py
│       └── risk_manager.py          # 리스크 관리
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx        # 메인 대시보드
│   │   │   ├── PositionList.tsx     # 포지션 리스트
│   │   │   ├── TradeHistory.tsx     # 매매 내역
│   │   │   ├── PerformanceChart.tsx # 성과 차트
│   │   │   └── Chatbot.tsx          # AI 챗봇 사이드바
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── Trading.tsx
│   │   │   └── Analytics.tsx
│   │   ├── api/
│   │   │   └── client.ts            # API 클라이언트
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── data/                            # PM-MCP data/ 공유
│   ├── trading.db                   # SQLite DB
│   ├── cache/                       # 캐시 (기존)
│   └── logs/                        # 로그
│
├── .env                             # API 키 (기존 재사용)
├── docker-compose.yml               # Optional
├── requirements.txt
└── README.md
```

---

## 🎯 핵심 기능 정의

### 1. 자동 매매 엔진
**PM-MCP 기반 종목 선정**
```python
# 매일 09:00 (시장 오픈 전)
1. PM-MCP ranking_advanced() 실행
   → 상위 5~10개 종목 선정
2. 각 종목에 대해 news_sentiment_analyze() 실행
   → 부정적 뉴스 종목 제외
3. 포지션 사이징 계산 (포트폴리오의 10%씩)
4. Alpaca API로 시장가 매수 주문
```

**청산 로직**
```python
# 매 5분마다 실행
1. 현재 포지션 조회
2. 각 포지션 체크:
   - 수익률 +10% 달성 → 50% 청산 (이익 실현)
   - 수익률 +20% 달성 → 전량 청산
   - 손실률 -5% 달성 → 전량 청산 (손절)
   - 보유 기간 7일 초과 → 전량 청산 (시간 손절)
```

### 2. 실시간 모니터링
- 현재 포지션 현황 (종목, 수량, 평균가, 현재가, 손익)
- 오늘의 매매 내역
- 누적 수익률 차트
- 리스크 지표 (Sharpe, Drawdown)

### 3. AI 챗봇
- Perplexity API를 통한 종목 리서치
- PM-MCP 분석 결과 요약 제공
- "AAPL에 대해 알려줘"
- "내 포트폴리오 평가해줘"

### 4. 백테스팅
- 과거 데이터로 전략 테스트
- 성과 지표 계산
- 파라미터 최적화

---

## 🔐 리스크 관리

### 포지션 사이징
```
단일 종목 최대 비중: 15%
전체 포지션 수: 최대 10개
1회 매매 금액: 포트폴리오의 10%
현금 비중: 최소 20% 유지
```

### 손실 제한
```
단일 종목 손절: -5%
일일 손실 한도: -3%
월간 손실 한도: -10%
최대 낙폭 한도: -20% (전체 중단)
```

### 안전장치
```
- Paper Trading 먼저 1개월 테스트
- 소액 실거래 (초기 $1,000)
- 단계적 자금 확대
- 주말/공휴일 자동 정지
```

---

## 📊 개발 로드맵

### Phase 1: 백엔드 코어 (3일)
**Day 1: 프로젝트 초기화**
- [ ] FastAPI 앱 구조 생성
- [ ] SQLite 데이터베이스 스키마 설계
- [ ] PM-MCP 모듈 Import 설정
- [ ] 기본 API 엔드포인트 구현

**Day 2: Alpaca 연동**
- [ ] Alpaca API 클라이언트 구현
- [ ] Paper Trading 계정 설정
- [ ] 주문 생성/취소/조회 기능
- [ ] 포지션 및 계좌 조회

**Day 3: 매매 로직**
- [ ] 전략 엔진 구현 (진입/청산 조건)
- [ ] 포지션 모니터링 서비스
- [ ] 리스크 관리 로직
- [ ] 스케줄러 설정 (자동 실행)

### Phase 2: 프론트엔드 (3일)
**Day 4: UI 기본 구조**
- [ ] React + Vite 프로젝트 생성
- [ ] Tailwind CSS 설정
- [ ] 레이아웃 및 라우팅
- [ ] API 클라이언트 설정

**Day 5: 대시보드**
- [ ] 포지션 리스트 컴포넌트
- [ ] 매매 내역 테이블
- [ ] 성과 차트 (Recharts)
- [ ] 실시간 업데이트 (SSE)

**Day 6: AI 챗봇**
- [ ] 챗봇 UI 구현
- [ ] Perplexity API 연동
- [ ] PM-MCP 결과 통합
- [ ] 대화 히스토리

### Phase 3: 테스트 및 최적화 (2일)
**Day 7: 백테스팅**
- [ ] 백테스팅 엔진 구현
- [ ] 과거 데이터 로드
- [ ] 성과 지표 계산
- [ ] 결과 시각화

**Day 8: 통합 테스트**
- [ ] Paper Trading 실전 테스트
- [ ] 버그 수정 및 최적화
- [ ] 로깅 및 모니터링 강화
- [ ] 문서화

---

## 🚀 실행 방법

### 개발 환경
```bash
# Backend
cd stock-manager/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd stock-manager/frontend
npm install
npm run dev
```

### 프로덕션 (로컬 24/7)
```bash
# PM2로 백그라운드 실행
pm2 start ecosystem.config.js

# 또는 systemd 서비스 등록
sudo systemctl start stock-manager
```

---

## 💰 예상 비용

| 항목 | 비용 | 비고 |
|------|------|------|
| Alpaca Paper Trading | **$0** | 무료 |
| Yahoo Finance | **$0** | 무료 |
| Alpha Vantage | **$0** | 무료 tier (500 req/day) |
| Finnhub | **$0** | 무료 tier (60 req/min) |
| Perplexity API | **기존** | PM-MCP 공유 |
| 로컬 서버 | **$0** | 개인 PC |
| **총계** | **$0/월** | 💚 |

---

## 🎓 참고 자료

### Alpaca API
- [Paper Trading Guide](https://alpaca.markets/docs/trading/paper-trading/)
- [Python SDK](https://github.com/alpacahq/alpaca-trade-api-python)

### PM-MCP 통합
- `mcp_server/tools/ranking_engine.py`
- `mcp_server/tools/portfolio_manager.py`
- `mcp_server/tools/news_sentiment.py`

### 자동매매 전략
- Mean Reversion
- Momentum Trading
- Relative Strength

---

## ⚠️ 면책사항

**이 시스템은 교육 및 연구 목적입니다.**
- Paper Trading으로 충분히 테스트 후 실거래를 고려하세요.
- 자동매매는 예상치 못한 손실을 발생시킬 수 있습니다.
- 투자 결정은 본인의 책임입니다.
- 시장 조건, 네트워크 장애 등으로 인한 손실에 대해 책임지지 않습니다.

---

## 📝 다음 단계

✅ 아키텍처 설계 완료
⬜ Alpaca 계정 생성 (Paper Trading)
⬜ 백엔드 초기 구조 생성
⬜ PM-MCP 통합 테스트
⬜ 기본 매매 로직 구현

---

**준비 완료! 빌드를 시작하시겠습니까?** 🚀
