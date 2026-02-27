# Phase 3 계획: 테마 + 팩터 통합

**작성일**: 2026-02-27
**작성자**: Claude Sonnet 4.5
**프로젝트**: PM-MCP v3.0.0
**Phase**: 3 (Planning)
**이전 Phase**: [Phase 2 완료 리포트](../../04-report/phase2-financial-sentiment.report.md)

---

## 📋 목차

1. [개요](#1-개요)
2. [목표 및 범위](#2-목표-및-범위)
3. [현황 분석](#3-현황-분석)
4. [구현 계획](#4-구현-계획)
5. [일정 및 마일스톤](#5-일정-및-마일스톤)
6. [리스크 및 대응](#6-리스크-및-대응)
7. [성공 지표](#7-성공-지표)

---

## 1. 개요

### 1.1 배경

**Phase 1-2 성과**:
- ✅ Phase 1: 기술적 지표 10개 + 한국 주식 지원
- ✅ Phase 2: 재무 팩터 20개 + 감성 분석 10개 + 백테스트

**현재 상황**:
- 📊 **팩터 분석**: 40개 팩터 완비 (기술 10 + 재무 20 + 감성 10)
- 🎯 **테마 발굴**: 기존 기능 존재 (interaction.py)
- ⚠️ **문제점**: 두 기능이 분리되어 시너지 효과 부족

**Phase 3 필요성**:
> "AI 테마에서 투자할 종목을 추천해줘" → 현재는 테마만 추출
> "NVDA의 팩터를 분석해줘" → 현재는 팩터만 분석
>
> ✅ Phase 3: 테마 발굴 + 팩터 분석 + 백테스트 → **통합 자동화**

### 1.2 비전

**"테마 기반 지능형 종목 추천 시스템"**

사용자가 관심 테마를 입력하면:
1. **테마 발굴**: 관련 종목 자동 추출
2. **팩터 분석**: 40개 팩터 자동 계산
3. **스코어 랭킹**: 종합 점수 기반 정렬
4. **백테스트 검증**: 과거 성과 확인
5. **투자 의견**: 상위 N개 종목 추천

**목표**: 1회 명령으로 테마 분석 → 종목 선정 → 검증까지 완료

---

## 2. 목표 및 범위

### 2.1 핵심 목표

**Primary Goal**:
- 기존 테마 발굴 기능과 Phase 2 팩터 분석을 통합하여 **원스톱 투자 분석 시스템** 구축

**Sub Goals**:
1. `theme_analyze_with_factors()` MCP 도구 추가
2. 테마별 팩터 스코어 자동 랭킹
3. 백테스트 성과 기반 종목 검증
4. 감성 분석 기반 테마 추천 강화

### 2.2 구현 범위

**Phase 3 In-Scope**:

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| **테마+팩터 통합 도구** | theme_analyze_with_factors() | 🔴 High |
| **테마별 랭킹** | 팩터 점수 기반 종목 정렬 | 🔴 High |
| **백테스트 통합** | 테마 종목 자동 백테스트 | 🟡 Medium |
| **감성 테마 추천** | 감성 점수 높은 테마 우선 | 🟡 Medium |
| **캐싱 레이어** | Redis 기반 팩터 캐싱 | 🟢 Low |
| **한국 테마 지원** | 한국 테마 + 팩터 통합 | 🟢 Low |

**Phase 3 Out-of-Scope** (Phase 4 후보):
- ❌ 포트폴리오 최적화 (자산 배분)
- ❌ 실시간 알림 시스템
- ❌ 시각화 대시보드
- ❌ 리스크 관리 (VaR, CVaR)

### 2.3 성공 기준

**Acceptance Criteria**:
1. ✅ `theme_analyze_with_factors()` 도구 작동
2. ✅ AI 테마 → 상위 5개 종목 추천 성공
3. ✅ 팩터 점수 기반 정렬 정확도 95%+
4. ✅ 백테스트 통합 (optional) 작동
5. ✅ Claude Desktop 실전 테스트 통과

---

## 3. 현황 분석

### 3.1 기존 테마 발굴 기능

**위치**: `mcp_server/tools/interaction.py`

**주요 함수**:

| 함수 | 기능 | 데이터 소스 |
|------|------|------------|
| `propose_themes()` | 테마 추천 | 뉴스 키워드 추출 |
| `explore_theme()` | 테마 상세 탐색 | ETF 보유 종목 + 뉴스 |
| `propose_tickers()` | 티커 제안 | THEME_SEEDS + ETF Holdings |
| `analyze_selection()` | 종목 분석 | rank_tickers_with_fundamentals |

**데이터 소스**:
- ETF Holdings (yfinance)
- THEME_SEEDS (수동 큐레이션)
- ETF_MAP (테마-ETF 매핑)
- 뉴스 키워드 (news_search)

**강점**:
- ✅ 도메인 지식 기반 큐레이션
- ✅ ETF 활용으로 정확도 높음
- ✅ 비동기 처리로 성능 우수

**약점**:
- ⚠️ 팩터 분석 미통합 (단순 fundamentals만)
- ⚠️ 백테스트 미연동
- ⚠️ 감성 분석 미활용

### 3.2 Phase 2 팩터 분석 기능

**모듈**:
- `financial_factors.py` - 재무 20개
- `sentiment_analysis.py` - 감성 10개
- `technical_indicators.py` - 기술 10개 (Phase 1)
- `factor_aggregator.py` - 통합 + 랭킹
- `backtest_engine.py` - 백테스트

**강점**:
- ✅ 40개 팩터 완비
- ✅ 정규화 + 종합 점수
- ✅ 백테스트 검증 가능

**약점**:
- ⚠️ 단일 종목 분석만 가능
- ⚠️ 테마 기반 자동 발굴 미지원

### 3.3 통합 시너지 효과

**현재 (분리)**:
```
사용자: "AI 테마 추천해줘"
Assistant: propose_themes() → ["AI", "Cloud", "Semiconductor"]

사용자: "AI 테마 종목 추천해줘"
Assistant: propose_tickers("AI") → ["NVDA", "MSFT", "GOOGL", ...]

사용자: "NVDA 분석해줘"
Assistant: comprehensive_analyze("NVDA") → 40개 팩터

사용자: "NVDA 백테스트해줘"
Assistant: backtest_strategy("NVDA") → 성과 지표
```

**Phase 3 (통합)**:
```
사용자: "AI 테마에서 투자할 종목 추천해줘"
Assistant: theme_analyze_with_factors("AI", top_n=5, include_backtest=True)
→ {
    "theme": "AI",
    "top_stocks": [
      {"ticker": "NVDA", "rank": 1, "score": 85.2, "backtest_return": 52.3%, "recommendation": "Strong Buy"},
      {"ticker": "AMD", "rank": 2, "score": 78.5, "backtest_return": 38.1%, "recommendation": "Buy"},
      ...
    ],
    "theme_sentiment": 0.65 (긍정),
    "recommendation": "AI 섹터는 강한 모멘텀, 상위 3종목 분할 매수 권장"
  }
```

**예상 효과**:
- ⏱️ 사용자 작업 시간: 5분 → 30초 (90% 단축)
- 🎯 추천 정확도: +30% (팩터 기반 검증)
- 📊 통합 분석: 테마 + 팩터 + 백테스트 원스톱

---

## 4. 구현 계획

### 4.1 아키텍처 설계

```
┌─────────────────────────────────────────────────────────┐
│                  theme_analyze_with_factors()            │
│                     (New MCP Tool)                       │
└─────────────────────────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────┐
│ propose_tickers  │ │ rank_stocks  │ │ backtest_    │
│     (Phase 1)    │ │  (Phase 2)   │ │ strategy     │
│                  │ │              │ │  (Phase 2)   │
└──────────────────┘ └──────────────┘ └──────────────┘
          │                 │                 │
          └─────────────────┴─────────────────┘
                            │
                            ▼
              ┌──────────────────────────┐
              │  Integrated Response     │
              │  - Top Stocks            │
              │  - Factor Scores         │
              │  - Backtest Results      │
              │  - Recommendation        │
              └──────────────────────────┘
```

### 4.2 Week 1: Core Integration (High Priority)

**목표**: 기본 통합 도구 구현

**Tasks**:

1. **ThemeFactorIntegrator 클래스 생성**
   - 파일: `mcp_server/tools/theme_factor_integrator.py`
   - 메서드:
     ```python
     @staticmethod
     def analyze_theme(
         theme: str,
         top_n: int = 5,
         include_backtest: bool = False,
         market: str = "US"
     ) -> Dict
     ```

2. **MCP 도구 추가**
   - `theme_analyze_with_factors()`
   - `mcp_app.py`에 추가

3. **통합 로직**
   ```python
   def analyze_theme(theme, top_n=5):
       # 1. 종목 발굴
       tickers = propose_tickers(theme)

       # 2. 팩터 랭킹
       ranked = rank_stocks(tickers, market="US")

       # 3. 상위 N개 선택
       top_stocks = ranked[:top_n]

       # 4. 결과 반환
       return {
           "theme": theme,
           "top_stocks": top_stocks,
           "total_candidates": len(tickers)
       }
   ```

**예상 결과**:
```json
{
  "theme": "AI",
  "top_stocks": [
    {
      "ticker": "NVDA",
      "rank": 1,
      "composite_score": 85.2,
      "factor_count": 38,
      "recommendation": "Strong Buy"
    },
    ...
  ]
}
```

### 4.3 Week 2: Backtest Integration (Medium Priority)

**목표**: 백테스트 자동 실행 추가

**Tasks**:

1. **백테스트 옵션 추가**
   ```python
   def analyze_theme(theme, top_n=5, include_backtest=True):
       top_stocks = ... # Week 1 로직

       if include_backtest:
           for stock in top_stocks:
               backtest_result = backtest_strategy(
                   ticker=stock['ticker'],
                   start_date="2024-01-01",
                   end_date="2024-12-31"
               )
               stock['backtest'] = {
                   'total_return': backtest_result['total_return'],
                   'sharpe_ratio': backtest_result['performance']['Sharpe_Ratio'],
                   'max_drawdown': backtest_result['performance']['Max_Drawdown']
               }

       return result
   ```

2. **성과 기반 재정렬** (optional)
   - 백테스트 수익률 가중치 추가
   - 팩터 점수 + 백테스트 성과 복합 점수

**예상 결과**:
```json
{
  "top_stocks": [
    {
      "ticker": "NVDA",
      "rank": 1,
      "composite_score": 85.2,
      "backtest": {
        "total_return": 52.3,
        "sharpe_ratio": 2.1,
        "max_drawdown": -18.5
      },
      "recommendation": "Strong Buy"
    }
  ]
}
```

### 4.4 Week 3: Sentiment-Enhanced Themes (Medium Priority)

**목표**: 감성 분석 기반 테마 추천 강화

**Tasks**:

1. **테마 감성 분석**
   ```python
   def get_theme_sentiment(theme: str) -> float:
       # 테마 관련 뉴스 감성 분석
       news = search_news([theme], lookback_days=7)
       sentiments = [analyze_sentiment(article) for article in news]
       return np.mean(sentiments)
   ```

2. **propose_themes 개선**
   - 기존: 뉴스 키워드만
   - 개선: 뉴스 + 감성 점수
   - 감성 점수 높은 테마 우선 순위

3. **테마 감성 리포트**
   ```json
   {
     "theme": "AI",
     "theme_sentiment": 0.68,
     "sentiment_label": "Bullish",
     "news_volume": 150,
     "trending": true
   }
   ```

### 4.5 Week 4: Caching Layer (Low Priority)

**목표**: 성능 최적화

**Tasks**:

1. **Redis 캐싱 레이어**
   - 파일: `mcp_server/tools/cache_layer.py`
   - TTL: 24시간
   - 캐시 키: `factor:{ticker}:{date}`

2. **캐싱 통합**
   ```python
   def calculate_all_with_cache(ticker, market):
       cache_key = f"factor:{ticker}:{date.today()}"

       # 캐시 확인
       cached = redis.get(cache_key)
       if cached:
           return json.loads(cached)

       # 계산 + 캐싱
       factors = FinancialFactors.calculate_all(ticker, market)
       redis.setex(cache_key, 86400, json.dumps(factors))
       return factors
   ```

3. **성능 측정**
   - Before: 종목당 3-5초
   - After: 종목당 0.1-0.3초
   - 예상 개선: **10배 향상**

---

## 5. 일정 및 마일스톤

### 5.1 전체 일정 (4주)

```
Phase 3: 테마 + 팩터 통합 (4 weeks)
├─ Week 1: Core Integration         (High Priority)
│   ├─ ThemeFactorIntegrator 클래스
│   ├─ theme_analyze_with_factors() 도구
│   └─ 기본 통합 로직
├─ Week 2: Backtest Integration     (Medium Priority)
│   ├─ 백테스트 자동 실행
│   ├─ 성과 기반 재정렬
│   └─ 종합 리포트
├─ Week 3: Sentiment Enhancement    (Medium Priority)
│   ├─ 테마 감성 분석
│   ├─ propose_themes 개선
│   └─ 감성 기반 추천
└─ Week 4: Optimization             (Low Priority)
    ├─ Redis 캐싱 레이어
    ├─ 성능 최적화
    └─ 한국 테마 지원 (optional)
```

### 5.2 주요 마일스톤

| Week | 마일스톤 | 검증 기준 |
|------|---------|----------|
| Week 1 | 기본 통합 완료 | "AI 테마 추천" → 상위 5개 종목 출력 |
| Week 2 | 백테스트 통합 | 각 종목의 백테스트 수익률 표시 |
| Week 3 | 감성 강화 | 테마 감성 점수 포함 |
| Week 4 | 최적화 완료 | 응답 시간 5초 이내 |

### 5.3 테스트 계획

**Test Cases**:

1. **기본 테마 분석**
   ```
   Input: theme_analyze_with_factors("AI", top_n=5)
   Expected: 5개 종목 + 팩터 점수 + 추천 등급
   ```

2. **백테스트 포함**
   ```
   Input: theme_analyze_with_factors("AI", top_n=3, include_backtest=True)
   Expected: 3개 종목 + 백테스트 성과
   ```

3. **한국 테마**
   ```
   Input: theme_analyze_with_factors("반도체", market="KR")
   Expected: 삼성전자, SK하이닉스 등 포함
   ```

---

## 6. 리스크 및 대응

### 6.1 기술적 리스크

| 리스크 | 가능성 | 영향도 | 대응 방안 |
|--------|--------|--------|-----------|
| **API Rate Limit** | High | Medium | 캐싱 + 요청 분산 |
| **성능 저하** | Medium | High | Redis 캐싱 필수화 |
| **데이터 품질** | Medium | Medium | 다중 소스 폴백 |
| **통합 복잡도** | Low | Medium | 점진적 통합 (Week 단위) |

### 6.2 일정 리스크

| 리스크 | 대응 |
|--------|------|
| Week 1 지연 | Week 4 (최적화) 생략 |
| Week 2 지연 | 백테스트 optional로 변경 |
| Week 3 지연 | 감성 강화 Phase 4로 이연 |

### 6.3 품질 리스크

**완화 전략**:
- ✅ 주간 Claude Desktop 테스트
- ✅ Phase 2 테스트 케이스 재사용
- ✅ PDCA Check 단계 적용

---

## 7. 성공 지표

### 7.1 정량적 지표

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| **Match Rate** | ≥ 95% | Gap 분석 |
| **응답 시간** | ≤ 5초 | Claude Desktop 실측 |
| **추천 정확도** | ≥ 80% | 백테스트 수익률 검증 |
| **팩터 커버리지** | ≥ 35/40 | 종목당 평균 팩터 수 |

### 7.2 정성적 지표

- ✅ 사용자 1회 명령으로 테마 → 종목 → 검증 완료
- ✅ 기존 분리 기능 대비 사용성 개선
- ✅ Claude Desktop 실전 테스트 통과

### 7.3 비교 지표

**Before (Phase 2)**:
- 테마 추천: `propose_themes()`
- 종목 발굴: `propose_tickers(theme)`
- 팩터 분석: `comprehensive_analyze(ticker)`
- 백테스트: `backtest_strategy(ticker)`
- **총 4단계**

**After (Phase 3)**:
- 통합 분석: `theme_analyze_with_factors(theme, include_backtest=True)`
- **1단계** 🚀

---

## 8. 다음 단계

### 8.1 즉시 조치

1. ✅ Phase 3 Plan 승인
2. 🔄 Phase 3 Design 문서 작성
3. 🚀 Week 1 구현 시작

### 8.2 Phase 4 후보

**우선순위별 제안**:

1. **포트폴리오 최적화** (High)
   - 멀티 팩터 포트폴리오 구성
   - 리밸런싱 전략
   - 자산 배분 최적화

2. **실시간 알림** (Medium)
   - 팩터 점수 변화 알림
   - 매수/매도 시그널
   - 이메일/Slack 통합

3. **시각화 대시보드** (Low)
   - 팩터 레이더 차트
   - 백테스트 자산 곡선
   - 섹터별 히트맵

---

**계획 작성자**: Claude Sonnet 4.5
**작성 완료일**: 2026-02-27 17:30 KST
**다음 단계**: Phase 3 Design 문서 작성
