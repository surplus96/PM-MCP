# PM-MCP (Portfolio Management MCP Server)

AI 기반 포트폴리오 관리 및 투자 분석을 위한 MCP(Model Context Protocol) 서버입니다.

## 주요 기능

### 테마 기반 투자 분석

#### 1. 테마 추천 (`propose_themes_tool`)
최근 시장 동향을 분석하여 투자 테마를 자동 추천합니다.

```python
propose_themes_tool(
    lookback_days=7,      # 분석 기간 (일)
    max_themes=5          # 최대 추천 테마 수
)
```

#### 2. 테마 탐색 (`explore_theme_tool`)
특정 투자 테마에 대한 상세 분석을 제공합니다.

```python
explore_theme_tool(
    theme='AI',           # 분석할 테마
    lookback_days=7       # 뉴스 검색 기간
)
```

#### 3. 티커 제안 (`propose_tickers_tool`)
선택한 테마에 적합한 종목들을 추천합니다.

```python
propose_tickers_tool(
    theme='AI'            # 대상 테마
)
```

#### 4. 정밀 분석 (`analyze_selection_tool`)
선택된 종목들에 대한 심층 분석을 수행합니다.

```python
analyze_selection_tool(
    theme='AI',
    tickers=['AAPL', 'MSFT', 'NVDA']
)
```

#### 5. 낙폭 매수 후보 분석 (`analyze_dip_candidates_tool`)
테마 내에서 단기 조정을 받은 매수 기회를 찾습니다.

```python
analyze_dip_candidates_tool(
    theme='AI',
    tickers_csv='AAPL,MSFT,NVDA',
    drawdown_min=0.2,     # 최소 낙폭 비율
    event_min=0.5,        # 최소 이벤트 점수
    ret10_min=0,          # 최소 10일 수익률
    top_n=5               # 상위 N개 후보
)
```

### 📊 포트폴리오 분석

#### 1. 자연어 포트폴리오 분석 (`portfolio_analyze_nl_tool`)
자연어로 보유주를 입력하여 간편하게 분석합니다.

```python
portfolio_analyze_nl_tool(
    holdings_text='AAPL@2024-10-01:185, LLY 2024-09-15 520, NVO',
    save=True             # Obsidian에 자동 저장
)
```

**입력 형식:**
- `TICKER@날짜:매수가` - 전체 정보
- `TICKER 날짜 매수가` - 공백 구분
- `TICKER` - 티커만 (현재가로 평가)

#### 2. 기본 포트폴리오 평가 (`portfolio_evaluate`)
보유 종목들의 기본 메트릭을 평가합니다.

```python
portfolio_evaluate(
    holdings=['AAPL', 'MSFT', 'NVDA']
)
```

#### 3. 상세 포트폴리오 평가 (`portfolio_evaluate_detailed`)
페이즈, 모멘텀, 변동성, 낙폭, 상관관계 등 종합 분석을 제공합니다.

```python
portfolio_evaluate_detailed(
    holdings=['AAPL', 'MSFT', 'NVDA']
)
```

**분석 항목:**
- **페이즈 분석**: 각 종목의 현재 투자 단계
- **모멘텀**: 단기/중기 추세 강도
- **변동성**: 리스크 수준 평가
- **낙폭**: 고점 대비 하락률
- **상관관계**: 포트폴리오 분산 효과

### 📈 시장 데이터

#### 1. 가격 데이터 조회 (`market_get_prices`)
종목의 과거 가격 데이터를 조회합니다.

```python
market_get_prices(
    ticker='AAPL',
    start='2024-01-01',   # 시작일 (선택)
    end='2024-12-31',     # 종료일 (선택)
    interval='1d'         # 간격: 1d, 1wk, 1mo
)
```

#### 2. 페이지네이션 가격 조회 (`market_get_prices_paginated`)
대용량 데이터를 페이지 단위로 조회합니다.

```python
market_get_prices_paginated(
    ticker='AAPL',
    cursor=0,             # 페이지 커서
    page_size=100         # 페이지 크기
)
```

#### 3. 요약 가격 데이터 (`market_get_prices_summary`)
집계된 가격 데이터를 조회합니다.

```python
market_get_prices_summary(
    ticker='AAPL',
    period='1y',          # 기간: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    interval='1d',        # 간격: 1d, 1wk, 1mo
    agg='W'               # 집계: D(일), W(주), M(월)
)
```

#### 4. CSV 내보내기 (`market_write_prices_csv`)
가격 데이터를 CSV 파일로 저장합니다.

```python
market_write_prices_csv(
    ticker='AAPL',
    start='2024-01-01',
    end='2024-12-31'
)
```

### 📰 뉴스 및 공시

#### 1. 뉴스 검색 (`news_search`)
종목 또는 테마 관련 뉴스를 검색합니다.

```python
news_search(
    queries=['AI', 'semiconductor'],
    lookback_days=7,      # 검색 기간
    max_results=10        # 최대 결과 수
)
```

#### 2. 뉴스 검색 로그 (`news_search_log_tool`)
테마별로 뉴스를 검색하고 로그를 남깁니다.

```python
news_search_log_tool(
    queries=['NVIDIA earnings', 'AI regulation'],
    theme='AI',           # 테마 태그
    lookback_days=7,
    max_results=10
)
```

#### 3. SEC 공시 조회 (`filings_fetch_recent`)
최근 SEC 공시 문서를 조회합니다.

```python
filings_fetch_recent(
    ticker='AAPL',
    forms=['10-K', '10-Q', '8-K'],  # 공시 유형 필터
    limit=10              # 최대 결과 수
)
```

**주요 공시 유형:**
- `10-K`: 연간 보고서
- `10-Q`: 분기 보고서
- `8-K`: 주요 이벤트 보고서
- `DEF 14A`: 주주총회 위임장
- `S-1`: 기업공개 등록서

### 🎨 시각화 및 리포트

#### 1. 테마 프레젠테이션 (`present_theme`)
테마 분석 결과를 차트와 함께 표시합니다.

```python
present_theme(
    theme='AI',
    tickers_csv='AAPL,MSFT,NVDA',
    chart_days=90,        # 차트 기간
    with_images=False,    # 이미지 포함 여부
    ma_windows=[20, 50],  # 이동평균선
    colors=['blue', 'red', 'green'],
    yscale='linear'       # 'linear' 또는 'log'
)
```

#### 2. 포트폴리오 프레젠테이션 (`present_portfolio`)
보유주 현황을 시각적으로 표시합니다.

```python
present_portfolio(
    tickers_csv='AAPL,MSFT,NVDA',
    history_days=30,      # 히스토리 기간
    with_images=False,
    ma_windows=[20, 50],
    colors=['blue', 'red', 'green'],
    yscale='linear'
)
```

#### 3. 테마 리포트 생성 (`create_theme_report`)
테마 분석 리포트를 생성합니다.

```python
create_theme_report(
    theme='AI',
    tickers_csv='AAPL,MSFT,NVDA'
)
```

#### 4. 포트폴리오 페이즈 리포트 (`create_portfolio_phase_report`)
포트폴리오의 페이즈 분석 리포트를 생성합니다.

```python
create_portfolio_phase_report(
    tickers_csv='AAPL,MSFT,NVDA'
)
```

### 📝 Obsidian 연동

#### 1. Obsidian 노트 작성 (`obsidian_write`)
분석 결과를 Obsidian vault에 저장합니다.

```python
obsidian_write(
    note_path='Investments/AI_Theme_Analysis.md',
    body='# 분석 내용\n...',
    front_matter={
        'tags': ['투자', 'AI'],
        'date': '2024-12-07'
    }
)
```

#### 2. 테마 저장 (`present_theme_save`)
테마 분석을 Obsidian에 저장합니다.

```python
present_theme_save(
    theme='AI',
    tickers_csv='AAPL,MSFT,NVDA',
    with_images=True
)
```

#### 3. 포트폴리오 저장 (`present_portfolio_save`)
포트폴리오 분석을 Obsidian에 저장합니다.

```python
present_portfolio_save(
    tickers_csv='AAPL,MSFT,NVDA',
    with_images=True
)
```

### 🔧 분석 도구

#### 1. 종목 랭킹 (`analytics_rank`)
후보 종목들을 점수화하여 순위를 매깁니다.

```python
analytics_rank(
    candidates=[
        {'ticker': 'AAPL', 'score': 85},
        {'ticker': 'MSFT', 'score': 90}
    ],
    use_dip_bonus=True,   # 낙폭 보너스 적용
    dip_weight=0.12,      # 낙폭 가중치
    auto_hydrate=True     # 자동 데이터 보강
)
```

#### 2. 리포트 생성 (`reports_generate`)
커스텀 리포트를 생성합니다.

```python
reports_generate(
    payload={
        'type': 'theme_analysis',
        'theme': 'AI',
        'tickers': ['AAPL', 'MSFT', 'NVDA'],
        'options': {...}
    }
)
```

## 워크플로우 예시

### 완전한 테마 분석 워크플로우

```python
# 1단계: 테마 추천
themes = propose_themes_tool(lookback_days=7, max_themes=5)

# 2단계: 특정 테마 탐색
details = explore_theme_tool(theme='AI', lookback_days=7)

# 3단계: 종목 추천
tickers = propose_tickers_tool(theme='AI')

# 4단계: 선택 종목 분석
analysis = analyze_selection_tool(
    theme='AI',
    tickers=['NVDA', 'MSFT', 'GOOGL']
)

# 5단계: 낙폭 매수 기회 찾기
dip_candidates = analyze_dip_candidates_tool(
    theme='AI',
    tickers_csv='NVDA,MSFT,GOOGL',
    top_n=3
)

# 6단계: 리포트 저장
present_theme_save(
    theme='AI',
    tickers_csv='NVDA,MSFT,GOOGL',
    with_images=True
)
```

### 포트폴리오 모니터링 워크플로우

```python
# 1단계: 간단 분석 (자연어)
portfolio_analyze_nl_tool(
    holdings_text='NVDA@2024-10-15:140, MSFT@2024-09-01:420, AAPL',
    save=True
)

# 2단계: 상세 분석
detailed = portfolio_evaluate_detailed(
    holdings=['NVDA', 'MSFT', 'AAPL']
)

# 3단계: 시각화 및 저장
present_portfolio_save(
    tickers_csv='NVDA,MSFT,AAPL',
    with_images=True
)
```

## 설치 및 사용

### MCP 서버 설정

Claude Desktop의 설정 파일에 다음을 추가하세요:

```json
{
  "mcpServers": {
    "pm-mcp": {
      "command": "python",
      "args": ["-m", "pm_mcp"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/path/to/your/vault"
      }
    }
  }
}
```

### 환경 변수

- `OBSIDIAN_VAULT_PATH`: Obsidian vault 경로 (선택)

## 데이터 소스

- **시장 데이터**: Yahoo Finance API
- **뉴스**: 통합 뉴스 검색 API
- **공시**: SEC EDGAR API

## 라이선스

MIT License
