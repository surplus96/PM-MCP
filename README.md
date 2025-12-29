## PM-MCP (Portfolio Manager MCP Agent)

**개요**: MCP 서버 기반 펀드 매니저 에이전트. 뉴스·재무·공시 데이터를 수집/요약/지식화하고, 후보군 랭킹과 리포트를 생성하여 옵시디언으로 정리합니다. Claude 호스트앱에서 도구 호출로 전 과정을 대화형으로 제어합니다.
- 타겟: 미국 주식 중심(확장 가능)
- 호스트앱: Claude (MCP 연동)

### 주요 프로세스
- 신규 투자 진행 프로세스:
  1. 전반적 시장/섹터/기업 동향 파악
  2. 사용자에게 종목 카테고리 추천
  3. 사용자 지정 종목·테마 정밀 파악
  4. 후보 기업/종목 리스트업 및 데이터 수집
  5. 분석·평가·랭킹 및 리포트 작성(예상 이익률·근거)
  6. 옵시디언으로 문서화·시각화·지식 그래프 활용
- 보유 종목 진단/알림 프로세스:
  1. 보유 종목 진단 및 페이즈(상승/유지/불안정/적신호) 알림
  2. 적신호 단계 시 정밀 분석 및 대응 제안

### 아키텍처 요약
- Claude 호스트앱 + MCP 서버(도구 제공)
- 데이터 소스:
  - 뉴스/동향: Perplexity MCP
  - 시세/재무: yfinance(우선), Alpha Vantage/Finnhub/Polygon.io(확장)
  - 공시/실적: SEC EDGAR API
- 분석/랭킹: 팩터 + 이벤트/모멘텀/리스크 스코어
- 스토리지: SQLite 캐시/운영, 옵시디언 Markdown, (선택) Neo4j
- 스케줄링: APScheduler (데일리/주간 잡)

### 사용 라이브러리
- 핵심: fastapi(선택), pydantic, requests, pandas, numpy, yfinance, python-dateutil, APScheduler, jinja2, diskcache, tqdm
- 선택: alpha_vantage, sec-api 또는 직접 EDGAR, ta, vectorbt, neo4j(옵션), langchain-core, pyyaml, markdownify

### 핵심 MCP 도구(엔드포인트)
- market_data.get_prices(ticker, start, end, interval)
- market_data.get_fundamentals(ticker)
- news.search(query|tickers, lookback)
- filings.fetch(ticker, form, lookback)
- analytics.rank(candidates, criteria?)
- portfolio.evaluate(holdings)
- reports.generate(type, payload)
- obsidian.write(note_path, content, links)

### Claude 자연어 예시 프롬프트
- 테마 리포트: "AI 테마 주간 리포트 만들어줘. 티커는 AAPL, MSFT, NVDA 사용해."
  - 내부 호출: `create_theme_report(theme='AI', tickers_csv='AAPL,MSFT,NVDA')`
- 포트폴리오 페이즈: "내 보유종목 AAPL, MSFT, NVDA의 페이즈 리포트 만들어줘."
  - 내부 호출: `create_portfolio_phase_report(tickers_csv='AAPL,MSFT,NVDA')`
- 뉴스: "최근 일주일 AI 칩과 클라우드 성장 관련 뉴스 5개만 요약해줘."
  - 내부 호출: `news_search(queries=['AI chips','cloud growth'], lookback_days=7, max_results=5)`
- 공시: "AAPL의 최근 10-Q/8-K 3건 보여줘."
  - 내부 호출: `filings_fetch_recent(ticker='AAPL', forms=['10-Q','8-K'], limit=3)`
