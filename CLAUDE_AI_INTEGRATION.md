# Claude.ai 웹 서비스 연동 가이드

이 가이드는 PM-MCP를 Claude.ai 웹 서비스(https://claude.ai)에 연동하는 방법을 설명합니다.

## 📋 개요

Claude.ai는 커스텀 MCP 서버를 HTTP SSE (Server-Sent Events) 방식으로 연동할 수 있습니다. 로컬에서 실행되는 MCP 서버를 공개 URL로 노출시켜 Claude.ai가 접근할 수 있도록 합니다.

## 🛠️ 필요한 구성 요소

1. **MCP HTTP SSE 서버**: `mcp_server/mcp_app_http.py` (이미 생성됨 ✅)
2. **터널링 도구**: ngrok 또는 localtunnel
3. **Claude.ai Pro 계정**: 커스텀 MCP 서버 기능을 사용하려면 Pro 계정이 필요합니다

## 🚀 빠른 시작 (3가지 방법)

### 방법 1: Localtunnel 사용 (가장 쉬움, 계정 불필요)

```bash
# WSL Ubuntu 터미널에서 실행
cd /home/surplus96/projects/PM-MCP
bash start_with_localtunnel.sh
```

**장점**:
- 계정 생성 불필요
- 설치 및 설정 자동화
- 즉시 사용 가능

**단점**:
- URL이 매번 변경됨
- 연결 안정성이 ngrok보다 낮을 수 있음

---

### 방법 2: ngrok 사용 (권장)

#### Step 1: ngrok 설치

```bash
# WSL Ubuntu 터미널에서 실행
cd /home/surplus96/projects/PM-MCP
bash setup_ngrok.sh
```

#### Step 2: ngrok 인증

1. https://ngrok.com 에서 계정 생성 (무료)
2. https://dashboard.ngrok.com/get-started/your-authtoken 에서 인증 토큰 복사
3. 터미널에서 실행:

```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

#### Step 3: 서버 시작

```bash
cd /home/surplus96/projects/PM-MCP
bash start_with_ngrok.sh
```

**장점**:
- 안정적인 연결
- 무료 플랜에서도 고정 도메인 사용 가능 (제한적)
- 웹 UI로 요청/응답 모니터링 가능 (http://localhost:4040)

**단점**:
- 계정 생성 필요
- 무료 플랜은 세션이 종료되면 URL이 변경됨

---

### 방법 3: 수동 실행 (디버깅용)

#### Terminal 1: MCP 서버 실행

```bash
cd /home/surplus96/projects/PM-MCP
source .venv/bin/activate
python -m uvicorn mcp_server.mcp_app_http:app --host 0.0.0.0 --port 8010
```

#### Terminal 2: 터널 생성 (ngrok 또는 localtunnel)

**ngrok:**
```bash
ngrok http 8010
```

**localtunnel:**
```bash
npx localtunnel --port 8010
```

---

## 🔗 Claude.ai에 MCP 서버 연결하기

### Step 1: 공개 URL 확인

터널링 도구를 실행하면 다음과 같은 URL을 받게 됩니다:

**ngrok 예시:**
```
Forwarding: https://abc123.ngrok-free.app -> http://localhost:8010
```

**localtunnel 예시:**
```
your url is: https://random-word-1234.loca.lt
```

### Step 2: Claude.ai 설정

1. https://claude.ai 접속 후 로그인
2. 설정(Settings) → "Features" 또는 "Integrations" 메뉴로 이동
3. "Add Custom MCP Server" 또는 유사한 옵션 선택
4. 다음 정보 입력:

```
Server Name: PM-MCP
Server URL: https://your-tunnel-url.com/sse
Description: Portfolio Manager MCP Agent
```

**중요**: URL 끝에 `/sse`를 반드시 추가해야 합니다!

예시:
- ngrok: `https://abc123.ngrok-free.app/sse`
- localtunnel: `https://random-word-1234.loca.lt/sse`

### Step 3: 연결 테스트

Claude.ai 대화창에서 다음과 같이 테스트:

```
AAPL 주식의 최근 가격 데이터를 가져와줘
```

또는

```
사용 가능한 PM-MCP 도구 목록을 보여줘
```

---

## 🧪 연결 확인 방법

### 로컬에서 HTTP 엔드포인트 테스트

```bash
# 서버가 정상 동작하는지 확인
curl http://localhost:8010/sse

# 또는 웹 브라우저에서 접속
# http://localhost:8010
```

### 터널 URL로 테스트

```bash
# ngrok URL로 테스트
curl https://your-ngrok-url.ngrok-free.app/sse

# localtunnel URL로 테스트
curl https://your-url.loca.lt/sse
```

---

## 📊 사용 가능한 MCP 도구

PM-MCP는 87개의 도구를 제공합니다. 주요 도구:

### 시장 데이터
- `market_get_prices`: 주식 가격 데이터 조회
- `market_condition`: 현재 시장 상황 분석
- `market_get_prices_summary`: 가격 요약 통계

### 뉴스 및 감성 분석
- `news_search`: 뉴스 검색
- `news_sentiment_analyze`: 뉴스 감성 분석
- `finnhub_news`: Finnhub 뉴스 조회

### 포트폴리오 관리
- `portfolio_evaluate`: 포트폴리오 평가
- `portfolio_comprehensive`: 종합 포트폴리오 분석
- `portfolio_sectors`: 섹터 분석
- `portfolio_pnl`: 손익 계산

### 기술적 분석
- `technical_summary`: 기술적 지표 요약
- `technical_rsi`: RSI 지표
- `technical_macd`: MACD 지표
- `technical_bbands`: 볼린저 밴드

### 차트 생성
- `chart_candlestick`: 캔들스틱 차트
- `chart_portfolio_allocation`: 포트폴리오 배분 차트
- `chart_correlation_heatmap`: 상관관계 히트맵

### 종합 분석
- `stock_comprehensive_analysis`: 종합 주식 분석
- `stock_compare`: 주식 비교 분석
- `ranking_advanced`: 고급 종목 랭킹

### 리포트 생성
- `create_theme_report`: 테마 리포트 생성
- `create_portfolio_phase_report`: 포트폴리오 페이즈 리포트

---

## 🔧 문제 해결

### 문제 1: "Connection refused" 오류

**원인**: MCP 서버가 실행되지 않음

**해결**:
```bash
# 서버가 실행 중인지 확인
ps aux | grep uvicorn

# 서버 재시작
bash start_with_localtunnel.sh
```

### 문제 2: ngrok "ERR_NGROK_108" 오류

**원인**: 인증 토큰이 설정되지 않음

**해결**:
```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### 문제 3: Claude.ai에서 도구가 보이지 않음

**원인**: URL 형식 오류 또는 서버 미실행

**확인 사항**:
1. URL 끝에 `/sse`가 있는지 확인
2. 터널 URL이 유효한지 확인 (`curl` 테스트)
3. MCP 서버 로그 확인 (`cat mcp_server.log`)

### 문제 4: localtunnel "connection refused" 오류

**원인**: IP 차단 또는 임시 서비스 오류

**해결**:
```bash
# 다른 서브도메인으로 재시도
lt --port 8010 --subdomain your-custom-name
```

또는 ngrok 사용으로 전환

---

## 🌐 고급 설정

### 고정 도메인 사용 (ngrok 유료)

```bash
ngrok http 8010 --domain=your-fixed-domain.ngrok-free.app
```

### HTTPS 인증서 (자체 도메인)

자체 도메인을 사용하는 경우 Cloudflare Tunnel 또는 Caddy를 사용할 수 있습니다.

### 로그 확인

```bash
# 실시간 로그 모니터링
tail -f mcp_server.log
```

---

## 📝 사용 예시

Claude.ai에 연결한 후 다음과 같이 사용할 수 있습니다:

```
1. "AAPL, MSFT, GOOGL 주식의 최근 1개월 가격 추이를 보여줘"

2. "AI 관련 최근 뉴스 5개를 요약해줘"

3. "내 포트폴리오 [AAPL, MSFT, NVDA]를 종합 분석해줘"

4. "테크 섹터 상위 10개 종목의 랭킹을 보여줘"

5. "TSLA 주식의 RSI와 MACD를 분석해줘"
```

---

## 🔒 보안 고려사항

1. **API 키 보호**: `.env` 파일에 저장된 API 키가 노출되지 않도록 주의
2. **터널 보안**: ngrok 또는 localtunnel URL을 공개하지 마세요
3. **인증**: 프로덕션 환경에서는 API 키 또는 OAuth 인증 추가 권장
4. **방화벽**: 필요시 특정 IP만 접근 허용하도록 설정

---

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. MCP 서버 로그: `cat mcp_server.log`
2. ngrok 웹 UI: http://localhost:4040 (ngrok 사용 시)
3. Python 가상환경이 활성화되어 있는지 확인

---

## 🎉 연동 완료!

이제 Claude.ai에서 PM-MCP의 모든 기능을 사용할 수 있습니다. 포트폴리오 관리, 종목 분석, 뉴스 요약 등을 Claude.ai 대화형 인터페이스에서 편리하게 이용하세요!
