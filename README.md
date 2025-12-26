## PM-MCP (Portfolio Manager MCP Agent)

**개요**: MCP 서버 기반 펀드 매니저 에이전트. 뉴스·재무·공시 데이터를 수집/요약/지식화하고, 후보군 랭킹과 리포트를 생성하여 옵시디언으로 정리합니다. Claude 호스트앱에서 도구 호출로 전 과정을 대화형으로 제어합니다.
- 타겟: 미국 주식 중심(확장 가능)
- 호스트앱: Claude (MCP 연동)
- 본 문서는 프로젝트 계획(`project-plan.md`)을 실행 가능한 README로 정리한 것입니다.

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

### 디렉터리 구조 제안

```bash
PM-MCP/
  mcp_server/
    __init__.py
    main.py                  # MCP 서버 엔트리
    tools/
      market_data.py         # 시세, 재무, 캘린더
      news_search.py         # Perplexity MCP 래핑
      filings.py             # SEC EDGAR
      analytics.py           # 팩터/시그널/랭킹
      portfolio.py           # 보유종목 관리/평가
      obsidian.py            # 마크다운 생성/내보내기
      reports.py             # 템플릿 기반 리포트 작성
    prompts/
      summary.txt
      entity_extraction.json
      ranking_criteria.md
    config.py
  data/
    raw/
    interim/
    processed/
    cache/
  obsidian_vault/
    Markets/
    Companies/
    Portfolios/
    Templates/
  scripts/
    run_daily.sh
    backfill_prices.py
  .env.example
  requirements.txt
  README.md
```
### 환경 변수(.env)

```bash
OPENAI_API_KEY=...
LLM_PROVIDER=openai
ALPHA_VANTAGE_API_KEY=...
FINNHUB_API_KEY=...
PERPLEXITY_API_KEY=...
SEC_EDGAR_USER_AGENT="email@example.com PM-MCP"
OBSIDIAN_VAULT_PATH=/Users/choetaeyeong/projects/PM-MCP/obsidian_vault
```

### 사용 라이브러리
- 핵심: fastapi(선택), pydantic, requests, pandas, numpy, yfinance, python-dateutil, APScheduler, jinja2, diskcache, tqdm
- 선택: alpha_vantage, sec-api 또는 직접 EDGAR, ta, vectorbt, neo4j(옵션), langchain-core, pyyaml, markdownify

### 프롬프트 스키마(요약/엔티티)
```text
[Summary] 5-7문장: 핵심 뉴스/공시 포인트, 영향(매출/마진/가이던스/규제), 리스크.
[Entities JSON]
{
  "ticker": [], "company": [], "sector": [], "industry": [],
  "event": [], "metric": [], "catalyst": [], "risk": [], "sentiment": []
}
(단일 JSON 객체, 모든 키 배열, 중복 제거)
```

### 핵심 MCP 도구(엔드포인트)
- market_data.get_prices(ticker, start, end, interval)
- market_data.get_fundamentals(ticker)
- news.search(query|tickers, lookback)
- filings.fetch(ticker, form, lookback)
- analytics.rank(candidates, criteria?)
- portfolio.evaluate(holdings)
- reports.generate(type, payload)
- obsidian.write(note_path, content, links)

### 옵시디언 출력 규칙
- 파일명: Companies/{TICKER} - {Company}.md, Markets/{Theme}.md
- Front matter 예시:
```yaml
---
type: company
ticker: AAPL
date: 2025-10-28
scores: { quant: 45, qual: 22, momentum_risk: 15 }
phase: 유지
links:
  - url: "..."
---
```

### 로드맵(마일스톤)
- M0: 환경 준비(.env, 폴더) 0.5d
- M1: 스캐폴딩/요구사항(README, requirements) 1d
- M2: 커넥터 구현(yfinance, Perplexity, SEC) 2d
- M3: 분석/랭킹/페이즈 2d
- M4: 리포트·옵시디언 1d
- M5: MCP 연동/테스트 1d
- M6: 스케줄러·운영 0.5d
- M7: 확장(Alpha Vantage/Finnhub, Neo4j, 백테스트)
### 차별점(Differentiators) & 사이드킥 기능(Sidekicks)

- **테마-그래프 인텔리전스**: 뉴스/공시에서 추출한 엔티티를 "테마 그래프"로 연결(섹터→산업→밸류체인→키워드). 테마 강도 지수(TSI)와 자금 유입 시그널을 결합해 "테마 관성"을 측정.
- **이벤트-센서 네트워크**: 실적 발표, 가이던스 상향/하향, 인수/규제, 제품 출시, 공급망 등 이벤트를 실시간 센서로 모델링. 종목·테마·경쟁사에 전파되는 2차, 3차 파급효과를 추정.
- **어썸 샘플링 리포트**: 동일 테마 내 상위 3개/하위 3개 종목의 대비 리포트를 1페이지에 자동 생성. “왜 이 종목인가/아닌가” 근거를 구조화하여 의사결정 속도 향상.
- **포트폴리오 카운터팩추얼**: 보유 종목 교체 시나리오(what-if) 자동 제안. 리밸런싱 후보와 기대 수익-리스크 변화량을 수치화.
- **이벤트 D-캘린더**: 다음 2주 내 주요 캘린더(FDA, 실적, 제품 출하, 규제)를 요약하고 포트폴리오 민감도를 시뮬레이션.
- **옵시디언 지식 루프**: 생성 리포트의 핵심 인사이트를 지속 누적, 재사용. 과거 결론 대비 현재 데이터 변화량을 하이라이트하여 회귀 평가 가능.
- **오퍼레이션 보호장치**: 신뢰도 스코어(출처/신선도/일관성)로 저품질 정보를 차단. 편향·환각 방지를 위한 인용/교차검증 규칙 적용.

> 위 기능은 일반적인 스크레이핑·요약형 프로젝트 대비, "테마/이벤트/포트폴리오"의 삼각 결합과 옵시디언 기반 메모리 축적을 핵심 차별점으로 삼습니다.
### 성과 지표(KPIs) & 평가

- **알파 지표**: 벤치마크 대비 초과수익(월/분기), 정보비율(IR)
- **의사결정 속도**: 신규 테마→후보 리스트업→리포트 생성까지 소요 시간
- **신호 품질**: 이벤트 후 5/20/60 거래일 수익률 분포, 히트율
- **리포트 활용도**: 옵시디언 조회수, 재인용/링크 백 비율
- **신뢰도 스코어**: 출처 다양성, 신선도, 교차검증 일치도
- **운영 안정성**: 실패율, API 한도 초과율, 재시도 성공률
### 보안·프라이버시 & 운영 원칙

- **API 키/인증**: `.env`/키관리, 최소권한, 로테이션. SEC EDGAR User-Agent 명시.
- **데이터 거버넌스**: 출처·저작권 준수, 요약/발췌 규칙 문서화.
- **로깅/모니터링**: 구조화 로그(JSON), 주요 도구의 latency/오류율 대시보드화.
- **캐시/한도 관리**: diskcache + 백오프/재시도. 요약·랭킹은 idempotent 설계.
- **재현성**: 프롬프트 버저닝, 샘플 셋 고정, 회귀 테스트.
- **안전장치**: 과도한 레버리지/테마 집중 경고, 리스크 점수 상한.

### 랭킹 스코어 보강: 저점매수 가산점
- **목적**: 최근 고점 대비 딥이 존재하면서 단기 모멘텀(10일)이 회복되는 종목을 가중 반영하여 저점매수 알파를 노림.
- **산식(요약)**:
  - 딥 점수 dd_score = clamp((recent_high - last)/recent_high ÷ 0.30, 0..1)
  - 모멘텀 점수 mom_score = clamp((ret10 + 5%) ÷ 10%, 0..1)
  - 가산점 dip_bonus = dip_weight × [0.5×dd_score + 0.5×(dd_score×mom_score)]
- **옵션**:
  - `dip_weight`(기본 0.12)로 영향도 조절
  - `dip_score`를 사전 계산해 후보 입력에 직접 주입 가능(없으면 가격데이터로 자동 계산)
- **주의**: 급락 추세 지속에는 모멘텀 항이 낮아 보너스 자연 감소. 리스크 관리(손절·포지션 한도) 병행 권장.

### Claude 자연어 예시 프롬프트
- 테마 리포트: "AI 테마 주간 리포트 만들어줘. 티커는 AAPL, MSFT, NVDA 사용해."
  - 내부 호출: `create_theme_report(theme='AI', tickers_csv='AAPL,MSFT,NVDA')`
- 포트폴리오 페이즈: "내 보유종목 AAPL, MSFT, NVDA의 페이즈 리포트 만들어줘."
  - 내부 호출: `create_portfolio_phase_report(tickers_csv='AAPL,MSFT,NVDA')`
- 뉴스: "최근 일주일 AI 칩과 클라우드 성장 관련 뉴스 5개만 요약해줘."
  - 내부 호출: `news_search(queries=['AI chips','cloud growth'], lookback_days=7, max_results=5)`
- 공시: "AAPL의 최근 10-Q/8-K 3건 보여줘."
  - 내부 호출: `filings_fetch_recent(ticker='AAPL', forms=['10-Q','8-K'], limit=3)`

### 시각화/프레젠테이션 기본값(.env)
- PRESENT_THEME_CHART_DAYS: 테마 차트 기간(일) 기본값
- PRESENT_PORTFOLIO_HISTORY_DAYS: 포트폴리오 차트 기간(일)
- PRESENT_YSCALE: y축 스케일(linear|log)
- PRESENT_MA_WINDOWS: 이동평균 윈도우(쉼표 구분)
- PRESENT_COLORS: 기본 색상 팔레트(쉼표 구분 hex)
- PRESENT_NEWS_MAX: 뉴스 항목 수
- PRESENT_FILINGS_MAX: 공시 항목 수

Claude에서는 옵션을 생략하면 위 기본값이 적용됩니다.

### 점수 산정 고도화(설정)
- SCORE_WEIGHTS: 예) `growth=0.2,profitability=0.3,valuation=0.3,quality=0.2`
- SCORE_SECTOR_NEUTRAL: true/false (섹터별 상대 정규화 적용)
- 티커 제안: 테마→ETF(BOTZ/AIQ, SMH/SOXX, CLOU/WCLD, HACK/CIBR, ICLN/TAN, XBI/IBB, FINX/ARKF, DRIV/KARS) 보유종목 상위 10 추출, 실패 시 폴백
- Perplexity JSON 파싱: 응답이 마크다운/텍스트를 포함해도 대괄호 구간만 추출해 복구 후 파싱 시도

### 저장형 도구(Obsidian 연동)
- present_theme_save(theme, tickers_csv, with_images): `Markets/{theme}/Overview {date}.md`
- present_portfolio_save(tickers_csv, with_images): `Portfolios/Overview {date}.md`
- news_search_log_tool(queries, lookback_days, max_results, theme?): `Markets/{theme}/News Logs/News {date}.md`
- dip 후보: analyze_dip_candidates_tool → 노트/CSV/이미지 경로 반환
