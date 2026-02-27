# Phase 3 설계: 테마 + 팩터 통합

**작성일**: 2026-02-27
**작성자**: Claude Sonnet 4.5
**프로젝트**: PM-MCP v3.0.0
**Phase**: 3 (Design)
**이전 문서**: [Phase 3 계획](../../01-plan/features/phase3-theme-factor-integration.plan.md)

---

## 📋 목차

1. [설계 개요](#1-설계-개요)
2. [아키텍처 설계](#2-아키텍처-설계)
3. [모듈 상세 설계](#3-모듈-상세-설계)
4. [API 명세](#4-api-명세)
5. [데이터 모델](#5-데이터-모델)
6. [통합 전략](#6-통합-전략)
7. [에러 처리](#7-에러-처리)
8. [테스트 전략](#8-테스트-전략)
9. [구현 순서](#9-구현-순서)

---

## 1. 설계 개요

### 1.1 설계 목표

**Primary Goal**:
> 기존 테마 발굴 기능과 팩터 분석 기능을 통합하여 **원스톱 투자 분석 시스템** 구축

**설계 원칙**:
1. **최소 침습성**: 기존 코드 수정 최소화
2. **모듈 독립성**: ThemeFactorIntegrator는 독립 모듈로 설계
3. **성능 최적화**: 비동기 처리 + 캐싱 전략
4. **확장 가능성**: 한국 테마, 추가 팩터 지원 용이

### 1.2 핵심 컴포넌트

| 컴포넌트 | 파일 | 역할 |
|---------|------|------|
| **ThemeFactorIntegrator** | `theme_factor_integrator.py` | 통합 로직 구현 |
| **MCP Tool** | `mcp_app.py` | Claude Desktop 인터페이스 |
| **CacheLayer** (Week 4) | `cache_layer.py` | Redis 기반 캐싱 |
| **Existing Modules** | `interaction.py`, `factor_aggregator.py` | 재사용 |

### 1.3 통합 전략

**기존 기능 재사용**:
- ✅ `propose_tickers()` - 테마 기반 종목 발굴
- ✅ `rank_stocks()` - 팩터 기반 랭킹
- ✅ `backtest_strategy()` - 백테스트 검증

**신규 기능 추가**:
- 🆕 `theme_analyze_with_factors()` - 통합 분석 도구
- 🆕 `get_theme_sentiment()` - 테마 감성 분석
- 🆕 `cache_factors()` - 팩터 캐싱 (Week 4)

---

## 2. 아키텍처 설계

### 2.1 시스템 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│                    Claude Desktop Client                      │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ MCP Protocol
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    mcp_app.py (MCP Server)                    │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         theme_analyze_with_factors() Tool              │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│        ThemeFactorIntegrator (New Module)                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  analyze_theme(theme, top_n, include_backtest, ...)   │  │
│  │  get_theme_sentiment(theme)                            │  │
│  │  rank_theme_stocks(tickers, market)                    │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
          │                    │                    │
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  interaction.py │  │factor_aggregator│  │backtest_engine.py│
│                 │  │      .py        │  │                 │
│ propose_tickers │  │  rank_stocks    │  │backtest_strategy│
│ explore_theme   │  │  normalize_     │  │calculate_       │
│ THEME_SEEDS     │  │  factors        │  │performance      │
│ ETF_MAP         │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                    │                    │
          └────────────────────┴────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                   External Data Sources                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  yfinance   │  │  NewsAPI    │  │  SEC EDGAR  │          │
│  │  (ETF Data) │  │  (Sentiment)│  │  (Filings)  │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 데이터 흐름

**Phase 1: Theme Discovery**
```
User Input ("AI")
  → propose_tickers("AI")
  → ETF_MAP["AI"] → ["BOTZ", "AIQ"]
  → yfinance.Ticker("BOTZ").fund_holdings
  → ["NVDA", "MSFT", "GOOGL", "AMD", ...] (10-20 tickers)
```

**Phase 2: Factor Analysis**
```
Tickers ["NVDA", "MSFT", ...]
  → rank_stocks(tickers, market="US")
  → For each ticker:
      - FinancialFactors.calculate_all() → 20 factors
      - TechnicalFactors.calculate_all() → 10 factors
      - SentimentFactors.calculate_all() → 10 factors
  → normalize_factors() → 0-100 scale
  → calculate_composite_score() → weighted average
  → Sort by composite_score DESC
```

**Phase 3: Backtest (Optional)**
```
Top N Stocks
  → For each stock:
      - backtest_strategy(ticker, start_date, end_date)
      - Calculate CAGR, Sharpe, Max Drawdown
  → Append backtest results to stock data
```

**Phase 4: Result Aggregation**
```
{
  "theme": "AI",
  "top_stocks": [
    {"ticker": "NVDA", "rank": 1, "score": 85.2, "backtest": {...}},
    ...
  ],
  "theme_sentiment": 0.68,
  "recommendation": "Strong Buy"
}
```

### 2.3 모듈 의존성

```
ThemeFactorIntegrator
├── interaction.py
│   ├── news_search.py
│   ├── presenter.py
│   └── yfinance
├── factor_aggregator.py
│   ├── financial_factors.py
│   ├── technical_factors.py
│   └── sentiment_analysis.py
└── backtest_engine.py
    └── factor_aggregator.py
```

---

## 3. 모듈 상세 설계

### 3.1 ThemeFactorIntegrator 클래스

**파일 위치**: `mcp_server/tools/theme_factor_integrator.py`

#### 3.1.1 클래스 구조

```python
#!/usr/bin/env python3
"""
Theme Factor Integrator Module

테마 발굴과 팩터 분석을 통합하여 원스톱 투자 분석 제공
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import numpy as np

from mcp_server.tools.interaction import propose_tickers, explore_theme
from mcp_server.tools.factor_aggregator import FactorAggregator
from mcp_server.tools.backtest_engine import BacktestEngine
from mcp_server.tools.sentiment_analysis import SentimentFactors
from mcp_server.tools.news_search import search_news

logger = logging.getLogger(__name__)


class ThemeFactorIntegrator:
    """테마 + 팩터 통합 분석"""

    # 테마별 기본 설정
    THEME_CONFIG = {
        "AI": {
            "etfs": ["BOTZ", "AIQ"],
            "min_market_cap": 10_000_000_000,  # $10B
            "max_candidates": 15
        },
        "semiconductor": {
            "etfs": ["SMH", "SOXX"],
            "min_market_cap": 5_000_000_000,  # $5B
            "max_candidates": 12
        },
        "default": {
            "etfs": [],
            "min_market_cap": 1_000_000_000,  # $1B
            "max_candidates": 10
        }
    }

    @staticmethod
    def analyze_theme(
        theme: str,
        top_n: int = 5,
        include_backtest: bool = False,
        include_sentiment: bool = True,
        market: str = "US",
        backtest_start: str = "2024-01-01",
        backtest_end: str = "2024-12-31",
        factor_weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """테마 기반 종합 분석

        Args:
            theme: 테마 키워드 (예: "AI", "semiconductor")
            top_n: 상위 N개 종목 반환
            include_backtest: 백테스트 포함 여부
            include_sentiment: 테마 감성 분석 포함 여부
            market: 시장 (US/KR)
            backtest_start: 백테스트 시작일
            backtest_end: 백테스트 종료일
            factor_weights: 팩터 가중치 (optional)

        Returns:
            테마 분석 결과
        """
        pass

    @staticmethod
    def get_theme_sentiment(theme: str, lookback_days: int = 7) -> Dict:
        """테마 감성 분석

        Args:
            theme: 테마 키워드
            lookback_days: 분석 기간 (일)

        Returns:
            테마 감성 정보
        """
        pass

    @staticmethod
    def rank_theme_stocks(
        tickers: List[str],
        market: str = "US",
        factor_weights: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """테마 종목 랭킹 (팩터 기반)

        Args:
            tickers: 종목 리스트
            market: 시장
            factor_weights: 팩터 가중치

        Returns:
            랭킹된 종목 리스트
        """
        pass

    @staticmethod
    def enrich_with_backtest(
        stocks: List[Dict],
        start_date: str,
        end_date: str,
        market: str = "US"
    ) -> List[Dict]:
        """백테스트 정보 추가

        Args:
            stocks: 종목 리스트
            start_date: 백테스트 시작일
            end_date: 백테스트 종료일
            market: 시장

        Returns:
            백테스트 정보가 추가된 종목 리스트
        """
        pass

    @staticmethod
    def generate_recommendation(
        theme: str,
        top_stocks: List[Dict],
        theme_sentiment: Optional[Dict] = None
    ) -> Dict:
        """투자 추천 생성 (Week 3 Enhanced)

        Args:
            theme: 테마
            top_stocks: 상위 종목 리스트
            theme_sentiment: 테마 감성 정보

        Returns:
            구조화된 투자 추천 (Dict):
            - summary: str - 요약 텍스트
            - action: str - 액션 (BUY/WATCH/HOLD/AVOID)
            - action_detail: str - 액션 상세 설명
            - confidence: str - 신뢰도 (High/Medium/Low)
            - confidence_score: float - 신뢰도 점수 (0-1)
            - risk_level: str - 리스크 레벨 (High/Medium/Low)
            - total_score: float - 종합 점수 (0-9)
            - max_score: float - 최대 점수 (9.0)
            - signals: Dict - 상세 신호 정보
        """
        pass
```

#### 3.1.2 analyze_theme() 상세 설계

```python
@staticmethod
def analyze_theme(
    theme: str,
    top_n: int = 5,
    include_backtest: bool = False,
    include_sentiment: bool = True,
    market: str = "US",
    backtest_start: str = "2024-01-01",
    backtest_end: str = "2024-12-31",
    factor_weights: Optional[Dict[str, float]] = None
) -> Dict:
    """테마 기반 종합 분석"""

    try:
        logger.info(f"Analyzing theme: {theme}, top_n={top_n}, backtest={include_backtest}")

        # Step 1: 테마 종목 발굴
        tickers = propose_tickers(theme)
        if not tickers:
            return {
                'error': f'No tickers found for theme: {theme}',
                'theme': theme
            }

        logger.info(f"Found {len(tickers)} candidates for theme '{theme}'")

        # Step 2: 팩터 기반 랭킹
        ranked_stocks = ThemeFactorIntegrator.rank_theme_stocks(
            tickers=tickers,
            market=market,
            factor_weights=factor_weights
        )

        if not ranked_stocks:
            return {
                'error': f'No valid stocks after factor analysis',
                'theme': theme,
                'candidates': len(tickers)
            }

        # Step 3: 상위 N개 선택
        top_stocks = ranked_stocks[:top_n]

        # Step 4: 백테스트 추가 (optional)
        if include_backtest:
            logger.info(f"Running backtest for top {len(top_stocks)} stocks")
            top_stocks = ThemeFactorIntegrator.enrich_with_backtest(
                stocks=top_stocks,
                start_date=backtest_start,
                end_date=backtest_end,
                market=market
            )

        # Step 5: 테마 감성 분석 (optional)
        theme_sentiment = None
        if include_sentiment:
            try:
                theme_sentiment = ThemeFactorIntegrator.get_theme_sentiment(theme)
            except Exception as e:
                logger.warning(f"Theme sentiment analysis failed: {e}")

        # Step 6: 추천 생성
        recommendation = ThemeFactorIntegrator.generate_recommendation(
            theme=theme,
            top_stocks=top_stocks,
            theme_sentiment=theme_sentiment
        )

        # Step 7: 결과 반환
        return {
            'theme': theme,
            'market': market,
            'total_candidates': len(tickers),
            'analyzed_stocks': len(ranked_stocks),
            'top_n': top_n,
            'top_stocks': top_stocks,
            'theme_sentiment': theme_sentiment,
            'recommendation': recommendation,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Theme analysis failed: {e}")
        return {
            'error': str(e),
            'theme': theme
        }
```

#### 3.1.3 get_theme_sentiment() 상세 설계

```python
@staticmethod
def get_theme_sentiment(theme: str, lookback_days: int = 7) -> Dict:
    """테마 감성 분석"""

    try:
        # Step 1: 테마 관련 뉴스 수집
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_days)

        news_articles = search_news(
            keywords=[theme],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )

        if not news_articles:
            return {
                'sentiment_score': 0.0,
                'sentiment_label': 'Neutral',
                'news_volume': 0,
                'trending': False
            }

        # Step 2: 감성 분석
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()

        sentiments = []
        for article in news_articles:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            scores = analyzer.polarity_scores(text)
            sentiments.append(scores['compound'])

        # Step 3: 통계 계산
        avg_sentiment = np.mean(sentiments) if sentiments else 0.0
        sentiment_std = np.std(sentiments) if len(sentiments) > 1 else 0.0
        news_volume = len(news_articles)

        # Step 4: 트렌드 판단
        # 뉴스량이 많고 (>10) 긍정적이면 (>0.2) 트렌딩
        trending = news_volume > 10 and avg_sentiment > 0.2

        # Step 5: 레이블 결정
        if avg_sentiment > 0.3:
            label = 'Bullish'
        elif avg_sentiment > 0.1:
            label = 'Slightly Bullish'
        elif avg_sentiment > -0.1:
            label = 'Neutral'
        elif avg_sentiment > -0.3:
            label = 'Slightly Bearish'
        else:
            label = 'Bearish'

        return {
            'sentiment_score': round(avg_sentiment, 3),
            'sentiment_label': label,
            'sentiment_std': round(sentiment_std, 3),
            'news_volume': news_volume,
            'trending': trending,
            'momentum': momentum,  # Week 3: 'Strong Positive' | 'Positive' | 'Stable' | 'Negative' | 'Strong Negative'
            'momentum_score': round(momentum_score, 3),  # Week 3: 최근 vs 과거 감성 차이
            'confidence': confidence,  # Week 3: 'High' | 'Medium' | 'Low'
            'confidence_score': round(confidence_score, 3),  # Week 3: 0-1 신뢰도 점수
            'key_topics': key_topics,  # Week 3: 빈도 기반 키워드 추출 (최대 5개)
            'lookback_days': lookback_days
        }

    except Exception as e:
        logger.error(f"Theme sentiment analysis failed: {e}")
        return {
            'error': str(e),
            'sentiment_score': 0.0,
            'sentiment_label': 'Unknown'
        }
```

#### 3.1.4 rank_theme_stocks() 상세 설계

```python
@staticmethod
def rank_theme_stocks(
    tickers: List[str],
    market: str = "US",
    factor_weights: Optional[Dict[str, float]] = None
) -> List[Dict]:
    """테마 종목 랭킹 (팩터 기반)"""

    try:
        # Step 1: 팩터 기반 랭킹 (기존 함수 재사용)
        ranked = FactorAggregator.rank_stocks(
            tickers=tickers,
            market=market,
            include_technical=True,
            include_financial=True,
            include_sentiment=True,
            factor_weights=factor_weights
        )

        # Step 2: 에러 필터링
        valid_stocks = [s for s in ranked if 'error' not in s]

        # Step 3: 추천 등급 추가
        for stock in valid_stocks:
            score = stock['composite_score']
            stock['recommendation'] = FactorAggregator.get_recommendation(score)

        return valid_stocks

    except Exception as e:
        logger.error(f"Ranking theme stocks failed: {e}")
        return []
```

#### 3.1.5 enrich_with_backtest() 상세 설계

```python
@staticmethod
def enrich_with_backtest(
    stocks: List[Dict],
    start_date: str,
    end_date: str,
    market: str = "US"
) -> List[Dict]:
    """백테스트 정보 추가"""

    enriched = []

    for stock in stocks:
        ticker = stock['ticker']

        try:
            # Step 1: 백테스트 실행
            backtest_result = BacktestEngine.run_backtest(
                ticker=ticker,
                market=market,
                start_date=start_date,
                end_date=end_date,
                rebalance_period=30,
                buy_threshold=60.0,
                sell_threshold=40.0,
                initial_capital=10000.0
            )

            # Step 2: 주요 지표 추출
            perf = backtest_result.get('performance', {})
            stock['backtest'] = {
                'total_return': backtest_result.get('total_return', 0.0),
                'cagr': perf.get('CAGR', 0.0),
                'max_drawdown': perf.get('Max_Drawdown', 0.0),
                'sharpe_ratio': perf.get('Sharpe_Ratio', 0.0),
                'win_rate': perf.get('Win_Rate', 0.0),
                'trade_count': backtest_result.get('trade_count', 0)
            }

            logger.info(f"Backtest completed for {ticker}: {stock['backtest']['total_return']:.2f}%")

        except Exception as e:
            logger.warning(f"Backtest failed for {ticker}: {e}")
            stock['backtest'] = {
                'error': str(e),
                'total_return': None
            }

        enriched.append(stock)

    return enriched
```

#### 3.1.6 generate_recommendation() 상세 설계 (Week 3 Enhanced)

**Week 3에서 대폭 개선**: 문자열 반환 → 구조화된 Dict 반환

```python
@staticmethod
def generate_recommendation(
    theme: str,
    top_stocks: List[Dict],
    theme_sentiment: Optional[Dict] = None
) -> Dict:
    """투자 추천 생성 (Week 3 Enhanced)

    Week 3 개선사항:
    - 반환 타입: str → Dict (구조화된 출력)
    - 신호 점수화: factor + backtest + sentiment 각각 점수화 (0-9)
    - 리스크 평가: 팩터 약세, 백테스트 부진, 감성 변동성, 모멘텀 악화 체크
    - 액션 분류: BUY/WATCH/HOLD/AVOID (신호 강도 + 리스크 레벨 기반)
    - 신뢰도 평가: 종합 신호 점수 기반 High/Medium/Low
    """

    if not top_stocks:
        return {
            'summary': f"No valid stocks found for theme '{theme}'",
            'action': 'AVOID',
            'confidence': 'Low',
            'risk_level': 'N/A',
            'signals': {}
        }

    # Step 1: 신호 수집 및 점수화
    signals = {}

    # 1.1 팩터 점수 (0-3점)
    avg_score = np.mean([s['composite_score'] for s in top_stocks])
    signals['factor_score'] = round(avg_score, 1)
    factor_points = 3 if avg_score >= 70 else (2 if avg_score >= 60 else 1)

    # 1.2 백테스트 수익률 (0-3점)
    backtest_returns = [
        s['backtest']['total_return']
        for s in top_stocks
        if 'backtest' in s and s['backtest'].get('total_return') is not None
    ]
    avg_backtest = np.mean(backtest_returns) if backtest_returns else None
    backtest_points = 1  # 기본값
    if avg_backtest is not None:
        signals['backtest_return'] = round(avg_backtest, 1)
        if avg_backtest > 20:
            backtest_points = 3
        elif avg_backtest > 10:
            backtest_points = 2
        elif avg_backtest > 0:
            backtest_points = 1
        else:
            backtest_points = 0

    # 1.3 테마 감성 (0-3점 + 모멘텀 보너스)
    sentiment_points = 1  # 기본값
    if theme_sentiment and 'error' not in theme_sentiment:
        sentiment_score = theme_sentiment.get('sentiment_score', 0.0)
        momentum = theme_sentiment.get('momentum', 'Stable')
        trending = theme_sentiment.get('trending', False)

        signals['sentiment_score'] = sentiment_score
        signals['sentiment_momentum'] = momentum
        signals['trending'] = trending

        # 감성 점수화
        if trending and sentiment_score > 0.2:
            sentiment_points = 3  # Very Bullish
        elif sentiment_score > 0.2:
            sentiment_points = 2  # Bullish
        elif sentiment_score > -0.1:
            sentiment_points = 1  # Neutral
        else:
            sentiment_points = 0  # Bearish

        # 모멘텀 보너스/페널티
        if 'Positive' in momentum:
            sentiment_points += 0.5
        elif 'Negative' in momentum:
            sentiment_points -= 0.5

    # Step 2: 종합 신호 점수 (0-9)
    total_points = factor_points + backtest_points + sentiment_points
    max_points = 9.0

    # Step 3: 리스크 평가
    risk_factors = []
    if avg_score < 60:
        risk_factors.append("Weak fundamentals")
    if avg_backtest is not None and avg_backtest < 0:
        risk_factors.append("Negative historical performance")
    if theme_sentiment:
        sentiment_std = theme_sentiment.get('sentiment_std', 0)
        if sentiment_std > 0.3:
            risk_factors.append("High sentiment volatility")
        if 'Negative' in theme_sentiment.get('momentum', ''):
            risk_factors.append("Deteriorating sentiment")

    risk_level = 'High' if len(risk_factors) >= 3 else ('Medium' if len(risk_factors) >= 1 else 'Low')
    signals['risk_factors'] = risk_factors
    signals['risk_level'] = risk_level

    # Step 4: 추천 액션 및 신뢰도
    confidence_score = total_points / max_points
    confidence = 'High' if confidence_score >= 0.75 else ('Medium' if confidence_score >= 0.5 else 'Low')

    # 액션 결정 (신호 강도 + 리스크 레벨)
    if total_points >= 7 and risk_level != 'High':
        action = 'BUY'
        top_tickers = ', '.join([s['ticker'] for s in top_stocks[:3]])
        action_detail = f"Consider accumulating top 3 stocks: {top_tickers}"
    elif total_points >= 5 and risk_level != 'High':
        action = 'WATCH'
        top_tickers = ', '.join([s['ticker'] for s in top_stocks[:2]])
        action_detail = f"Monitor top stocks: {top_tickers}"
    elif total_points >= 4:
        action = 'HOLD'
        action_detail = "Wait for clearer signals or better entry points"
    else:
        action = 'AVOID'
        action_detail = "Consider alternative themes or wait for improvement"

    # Step 5: 요약 생성
    summary_parts = []
    if theme_sentiment and theme_sentiment.get('trending'):
        summary_parts.append(f"✅ '{theme}' theme is trending")
    if signals.get('factor_signal') == 'Strong':
        summary_parts.append(f"Strong fundamentals ({avg_score:.1f}/100)")
    if avg_backtest and avg_backtest > 10:
        summary_parts.append(f"Positive backtest ({avg_backtest:.1f}%)")
    if risk_level == 'High':
        summary_parts.append(f"⚠️ High risk: {', '.join(risk_factors[:2])}")

    summary = ' | '.join(summary_parts) if summary_parts else "Mixed signals"

    return {
        'summary': summary,
        'action': action,
        'action_detail': action_detail,
        'confidence': confidence,
        'confidence_score': round(confidence_score, 2),
        'risk_level': risk_level,
        'total_score': round(total_points, 1),
        'max_score': max_points,
        'signals': signals
    }
```

#### 3.1.7 rerank_by_performance() 상세 설계 (Week 2 Addition)

**Week 2에서 추가**: 팩터 점수와 백테스트 성과를 결합한 재정렬

```python
@staticmethod
def rerank_by_performance(
    stocks: List[Dict],
    factor_weight: float = 0.6,
    backtest_weight: float = 0.4
) -> List[Dict]:
    """성과 기반 재정렬 (Week 2)

    팩터 점수(60%)와 백테스트 수익률(40%)을 가중 결합하여 재정렬
    백테스트 데이터가 없는 종목은 리스트 뒤로 배치

    Returns:
        재정렬된 종목 리스트 (combined_score 포함)
    """
    # 백테스트 데이터가 있는 종목만 재정렬
    stocks_with_backtest = [
        s for s in stocks
        if 'backtest' in s and s['backtest'].get('total_return') is not None
    ]

    if not stocks_with_backtest:
        return stocks

    # 백테스트 수익률 정규화 (0-100 스케일)
    returns = [s['backtest']['total_return'] for s in stocks_with_backtest]
    min_return = min(returns)
    max_return = max(returns)

    for stock in stocks_with_backtest:
        factor_score = stock.get('composite_score', 50.0)
        bt_return = stock['backtest']['total_return']
        bt_score = ((bt_return - min_return) / (max_return - min_return)) * 100 if max_return > min_return else 50.0

        # 복합 점수 계산
        combined_score = (factor_score * factor_weight) + (bt_score * backtest_weight)
        stock['combined_score'] = round(combined_score, 2)
        stock['original_rank'] = stock.get('rank', 0)

    # 복합 점수 기준 재정렬
    stocks_with_backtest.sort(key=lambda x: x['combined_score'], reverse=True)

    # 랭킹 업데이트
    for i, stock in enumerate(stocks_with_backtest, 1):
        stock['rank'] = i

    # 백테스트 없는 종목은 뒤에 추가
    stocks_without_backtest = [s for s in stocks if s not in stocks_with_backtest]
    return stocks_with_backtest + stocks_without_backtest
```

#### 3.1.8 validate_backtest_quality() 상세 설계 (Week 2 Addition)

**Week 2에서 추가**: 백테스트 결과의 신뢰도 평가

```python
@staticmethod
def validate_backtest_quality(
    backtest_result: Dict
) -> Dict:
    """백테스트 품질 검증 (Week 2)

    거래 횟수, 샤프 비율, 최대 낙폭, 승률 기반으로 백테스트 신뢰도 평가

    Returns:
        {
            'quality_score': float (0-100),
            'grade': str (Excellent/Good/Fair/Poor),
            'issues': List[str],
            'warnings': List[str],
            'reliable': bool (quality_score >= 60)
        }
    """
    quality_score = 100.0
    issues = []
    warnings = []

    # 1. 거래 횟수 확인
    trade_count = backtest_result.get('trade_count', 0)
    if trade_count == 0:
        quality_score -= 50
        issues.append("No trades executed")
    elif trade_count < 3:
        quality_score -= 20
        warnings.append(f"Low trade count ({trade_count})")

    # 2. 샤프 비율 확인
    perf = backtest_result.get('performance', {})
    sharpe = perf.get('Sharpe_Ratio', 0)
    if sharpe < 0:
        quality_score -= 15
        warnings.append(f"Negative Sharpe ratio ({sharpe:.2f})")
    elif sharpe < 0.5:
        quality_score -= 5
        warnings.append(f"Low Sharpe ratio ({sharpe:.2f})")

    # 3. 최대 낙폭 확인
    max_dd = perf.get('Max_Drawdown', 0)
    if max_dd > 50:
        quality_score -= 20
        issues.append(f"Excessive drawdown ({max_dd:.1f}%)")
    elif max_dd > 30:
        quality_score -= 10
        warnings.append(f"High drawdown ({max_dd:.1f}%)")

    # 4. 승률 확인
    win_rate = perf.get('Win_Rate', 0)
    if win_rate < 30:
        quality_score -= 10
        warnings.append(f"Low win rate ({win_rate:.1f}%)")

    # 5. 품질 등급
    if quality_score >= 80:
        grade = "Excellent"
    elif quality_score >= 60:
        grade = "Good"
    elif quality_score >= 40:
        grade = "Fair"
    else:
        grade = "Poor"

    return {
        'quality_score': max(0, quality_score),
        'grade': grade,
        'issues': issues,
        'warnings': warnings,
        'reliable': quality_score >= 60
    }
```

---

## 4. API 명세

### 4.1 MCP Tool: theme_analyze_with_factors

**파일**: `mcp_server/mcp_app.py`

#### 4.1.1 Tool 정의

```python
@mcp.tool()
async def theme_analyze_with_factors(
    theme: str,
    top_n: int = 5,
    include_backtest: bool = False,
    include_sentiment: bool = True,
    market: str = "US",
    backtest_start: str = "2024-01-01",
    backtest_end: str = "2024-12-31"
) -> Dict:
    """테마 기반 종합 투자 분석

    테마를 입력하면 관련 종목을 발굴하고, 40개 팩터 기반으로 랭킹한 후,
    선택적으로 백테스트를 실행하여 투자 의견을 제공합니다.

    Args:
        theme: 테마 키워드 (예: "AI", "semiconductor", "biotech")
        top_n: 반환할 상위 종목 수 (기본: 5)
        include_backtest: 백테스트 실행 여부 (기본: False)
        include_sentiment: 테마 감성 분석 포함 여부 (기본: True)
        market: 시장 (US/KR, 기본: US)
        backtest_start: 백테스트 시작일 (YYYY-MM-DD, 기본: 2024-01-01)
        backtest_end: 백테스트 종료일 (YYYY-MM-DD, 기본: 2024-12-31)

    Returns:
        테마 분석 결과:
        {
            "theme": "AI",
            "market": "US",
            "total_candidates": 15,
            "analyzed_stocks": 12,
            "top_n": 5,
            "top_stocks": [
                {
                    "ticker": "NVDA",
                    "rank": 1,
                    "composite_score": 85.2,
                    "factor_count": 38,
                    "recommendation": "Strong Buy",
                    "backtest": {
                        "total_return": 52.3,
                        "cagr": 45.2,
                        "max_drawdown": -18.5,
                        "sharpe_ratio": 2.1,
                        "win_rate": 65.0,
                        "trade_count": 8
                    }
                },
                ...
            ],
            "theme_sentiment": {
                "sentiment_score": 0.68,
                "sentiment_label": "Bullish",
                "news_volume": 150,
                "trending": true
            },
            "recommendation": "✅ 'AI' theme is trending with bullish sentiment | Strong factor scores (avg: 82.3) | Strong backtest performance (avg: 45.2%) | Consider accumulating top 3 stocks: NVDA, AMD, AVGO"
        }

    Examples:
        # 기본 분석 (백테스트 제외)
        theme_analyze_with_factors("AI", top_n=5)

        # 백테스트 포함
        theme_analyze_with_factors("semiconductor", top_n=3, include_backtest=True)

        # 한국 테마
        theme_analyze_with_factors("반도체", market="KR", top_n=5)
    """
    try:
        from mcp_server.tools.theme_factor_integrator import ThemeFactorIntegrator

        result = ThemeFactorIntegrator.analyze_theme(
            theme=theme,
            top_n=top_n,
            include_backtest=include_backtest,
            include_sentiment=include_sentiment,
            market=market,
            backtest_start=backtest_start,
            backtest_end=backtest_end
        )

        return result

    except Exception as e:
        logger.error(f"theme_analyze_with_factors failed: {e}")
        return {
            'error': str(e),
            'theme': theme
        }
```

### 4.2 응답 예시

#### 4.2.1 성공 응답 (백테스트 포함)

```json
{
  "theme": "AI",
  "market": "US",
  "total_candidates": 15,
  "analyzed_stocks": 12,
  "top_n": 5,
  "top_stocks": [
    {
      "ticker": "NVDA",
      "rank": 1,
      "composite_score": 85.2,
      "factor_count": 38,
      "recommendation": "Strong Buy",
      "category_scores": {
        "profitability": 88.5,
        "health": 82.0,
        "efficiency": 79.3,
        "technical": 90.1,
        "sentiment": 85.7
      },
      "backtest": {
        "total_return": 52.3,
        "cagr": 45.2,
        "max_drawdown": -18.5,
        "sharpe_ratio": 2.1,
        "win_rate": 65.0,
        "trade_count": 8
      }
    },
    {
      "ticker": "AMD",
      "rank": 2,
      "composite_score": 78.5,
      "factor_count": 36,
      "recommendation": "Buy",
      "backtest": {
        "total_return": 38.1,
        "cagr": 32.5,
        "max_drawdown": -22.3,
        "sharpe_ratio": 1.7,
        "win_rate": 58.3,
        "trade_count": 7
      }
    },
    {
      "ticker": "AVGO",
      "rank": 3,
      "composite_score": 76.2,
      "factor_count": 37,
      "recommendation": "Buy",
      "backtest": {
        "total_return": 28.7,
        "cagr": 25.1,
        "max_drawdown": -15.8,
        "sharpe_ratio": 1.9,
        "win_rate": 62.5,
        "trade_count": 6
      }
    }
  ],
  "theme_sentiment": {
    "sentiment_score": 0.68,
    "sentiment_label": "Bullish",
    "sentiment_std": 0.15,
    "news_volume": 150,
    "trending": true,
    "lookback_days": 7
  },
  "recommendation": "✅ 'AI' theme is trending with bullish sentiment | Strong factor scores (avg: 80.0) | Strong backtest performance (avg: 39.7%) | Consider accumulating top 3 stocks: NVDA, AMD, AVGO",
  "analysis_timestamp": "2026-02-27T09:30:00.000Z"
}
```

#### 4.2.2 성공 응답 (백테스트 제외)

```json
{
  "theme": "biotech",
  "market": "US",
  "total_candidates": 12,
  "analyzed_stocks": 10,
  "top_n": 3,
  "top_stocks": [
    {
      "ticker": "VRTX",
      "rank": 1,
      "composite_score": 82.3,
      "factor_count": 35,
      "recommendation": "Strong Buy"
    },
    {
      "ticker": "REGN",
      "rank": 2,
      "composite_score": 75.8,
      "factor_count": 34,
      "recommendation": "Buy"
    },
    {
      "ticker": "AMGN",
      "rank": 3,
      "composite_score": 72.1,
      "factor_count": 36,
      "recommendation": "Buy"
    }
  ],
  "theme_sentiment": {
    "sentiment_score": 0.42,
    "sentiment_label": "Slightly Bullish",
    "news_volume": 45,
    "trending": false
  },
  "recommendation": "Theme sentiment: Slightly Bullish | Strong factor scores (avg: 76.7) | Monitor top stocks: VRTX, REGN"
}
```

#### 4.2.3 에러 응답

```json
{
  "error": "No tickers found for theme: unknown_theme",
  "theme": "unknown_theme"
}
```

---

## 5. 데이터 모델

### 5.1 테마 설정 모델

```python
THEME_CONFIG = {
    "theme_name": {
        "etfs": List[str],           # 관련 ETF 리스트
        "min_market_cap": float,     # 최소 시가총액 (USD)
        "max_candidates": int        # 최대 후보 종목 수
    }
}
```

**예시**:
```python
{
    "AI": {
        "etfs": ["BOTZ", "AIQ"],
        "min_market_cap": 10_000_000_000,
        "max_candidates": 15
    }
}
```

### 5.2 분석 결과 모델

```python
{
    "theme": str,                    # 테마 이름
    "market": str,                   # 시장 (US/KR)
    "total_candidates": int,         # 전체 후보 종목 수
    "analyzed_stocks": int,          # 팩터 분석 완료 종목 수
    "top_n": int,                    # 상위 N개
    "top_stocks": List[StockInfo],   # 상위 종목 리스트
    "theme_sentiment": ThemeSentiment,  # 테마 감성 정보
    "recommendation": str,           # 투자 추천
    "analysis_timestamp": str        # 분석 시간 (ISO format)
}
```

### 5.3 종목 정보 모델

```python
class StockInfo:
    ticker: str                      # 종목 코드
    rank: int                        # 랭킹
    composite_score: float           # 종합 점수 (0-100)
    factor_count: int                # 계산된 팩터 수
    recommendation: str              # 추천 등급
    category_scores: Dict[str, float]  # 카테고리별 점수 (optional)
    backtest: BacktestInfo           # 백테스트 정보 (optional)
```

### 5.4 백테스트 정보 모델

```python
class BacktestInfo:
    total_return: float              # 총 수익률 (%)
    cagr: float                      # 연평균 수익률 (%)
    max_drawdown: float              # 최대 낙폭 (%)
    sharpe_ratio: float              # 샤프 비율
    win_rate: float                  # 승률 (%)
    trade_count: int                 # 거래 횟수
    error: str                       # 에러 (optional)
```

### 5.5 테마 감성 모델

```python
class ThemeSentiment:
    sentiment_score: float           # 감성 점수 (-1 ~ 1)
    sentiment_label: str             # 레이블 (Bullish/Bearish/Neutral)
    sentiment_std: float             # 감성 표준편차
    news_volume: int                 # 뉴스 건수
    trending: bool                   # 트렌딩 여부
    lookback_days: int               # 분석 기간 (일)
    error: str                       # 에러 (optional)
```

---

## 6. 통합 전략

### 6.1 기존 모듈 재사용

**Phase 2 모듈 100% 재사용**:
- ✅ `propose_tickers()` - 테마 기반 종목 발굴
- ✅ `rank_stocks()` - 팩터 랭킹
- ✅ `backtest_strategy()` - 백테스트
- ✅ `calculate_composite_score()` - 종합 점수
- ✅ `get_recommendation()` - 추천 등급

**최소 침습 원칙**:
- `interaction.py` 수정 없음
- `factor_aggregator.py` 수정 없음
- `backtest_engine.py` 수정 없음

### 6.2 새로운 통합 로직

**ThemeFactorIntegrator**:
- 기존 함수 오케스트레이션
- 에러 처리 강화
- 결과 포맷팅

### 6.3 의존성 관리

```python
# theme_factor_integrator.py
from mcp_server.tools.interaction import propose_tickers, explore_theme
from mcp_server.tools.factor_aggregator import FactorAggregator
from mcp_server.tools.backtest_engine import BacktestEngine
from mcp_server.tools.sentiment_analysis import SentimentFactors
from mcp_server.tools.news_search import search_news
```

**순환 의존성 방지**:
- ThemeFactorIntegrator는 상위 레이어
- 다른 모듈은 ThemeFactorIntegrator 참조 금지

---

## 7. 에러 처리

### 7.1 에러 타입

| 에러 타입 | 원인 | 처리 방법 |
|----------|------|----------|
| **NoTickersFound** | 테마 종목 없음 | 에러 반환 + 대체 테마 제안 |
| **FactorCalculationFailed** | 팩터 계산 실패 | 해당 종목 스킵 + 로그 |
| **BacktestFailed** | 백테스트 실패 | backtest.error 필드에 기록 |
| **SentimentFailed** | 감성 분석 실패 | theme_sentiment=null |
| **APIRateLimit** | API 한도 초과 | 재시도 + 캐싱 |

### 7.2 에러 처리 전략

#### 7.2.1 Graceful Degradation

```python
# 백테스트 실패 시
try:
    backtest_result = BacktestEngine.run_backtest(...)
    stock['backtest'] = {...}
except Exception as e:
    logger.warning(f"Backtest failed for {ticker}: {e}")
    stock['backtest'] = {'error': str(e)}
    # 계속 진행 (백테스트 없이)
```

#### 7.2.2 Partial Success

```python
# 일부 종목 팩터 계산 실패 시
ranked_stocks = rank_stocks(tickers)
valid_stocks = [s for s in ranked_stocks if 'error' not in s]

if not valid_stocks:
    return {'error': 'No valid stocks after factor analysis'}

# 일부만 성공해도 계속 진행
top_stocks = valid_stocks[:top_n]
```

#### 7.2.3 Retry with Backoff

```python
# API Rate Limit 대응
import time

def rank_with_retry(tickers, max_retries=3):
    for attempt in range(max_retries):
        try:
            return rank_stocks(tickers)
        except RateLimitError:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Rate limit hit, retrying in {wait_time}s")
                time.sleep(wait_time)
            else:
                raise
```

### 7.3 로깅 전략

```python
# 로그 레벨
logger.info()      # 주요 단계 (테마 발굴, 랭킹, 백테스트)
logger.warning()   # 복구 가능 에러 (백테스트 실패, 감성 분석 실패)
logger.error()     # 치명적 에러 (전체 분석 실패)

# 로그 포맷
logger.info(f"Analyzing theme: {theme}, top_n={top_n}, backtest={include_backtest}")
logger.info(f"Found {len(tickers)} candidates for theme '{theme}'")
logger.info(f"Running backtest for top {len(top_stocks)} stocks")
logger.warning(f"Backtest failed for {ticker}: {e}")
logger.error(f"Theme analysis failed: {e}")
```

---

## 8. 테스트 전략

### 8.1 테스트 파일 구조

**파일**: `test_phase3_week1.py` (Week 1), `test_phase3_integration.py` (통합)

### 8.2 테스트 케이스

#### 8.2.1 Unit Tests

```python
def test_get_theme_sentiment():
    """테마 감성 분석 단위 테스트"""
    result = ThemeFactorIntegrator.get_theme_sentiment("AI", lookback_days=7)

    assert 'sentiment_score' in result
    assert -1 <= result['sentiment_score'] <= 1
    assert result['sentiment_label'] in ['Bullish', 'Bearish', 'Neutral', ...]
    assert result['news_volume'] >= 0

def test_rank_theme_stocks():
    """테마 종목 랭킹 단위 테스트"""
    tickers = ["NVDA", "MSFT", "GOOGL"]
    result = ThemeFactorIntegrator.rank_theme_stocks(tickers, market="US")

    assert len(result) <= len(tickers)
    assert all('composite_score' in s for s in result)
    assert all('recommendation' in s for s in result)

def test_generate_recommendation():
    """추천 생성 단위 테스트"""
    top_stocks = [
        {"ticker": "NVDA", "composite_score": 85.2},
        {"ticker": "AMD", "composite_score": 78.5}
    ]
    theme_sentiment = {"sentiment_label": "Bullish", "trending": True}

    recommendation = ThemeFactorIntegrator.generate_recommendation(
        "AI", top_stocks, theme_sentiment
    )

    assert isinstance(recommendation, str)
    assert len(recommendation) > 0
```

#### 8.2.2 Integration Tests

```python
def test_analyze_theme_basic():
    """기본 테마 분석 통합 테스트"""
    result = ThemeFactorIntegrator.analyze_theme(
        theme="AI",
        top_n=3,
        include_backtest=False,
        include_sentiment=True,
        market="US"
    )

    assert 'theme' in result
    assert result['theme'] == "AI"
    assert 'top_stocks' in result
    assert len(result['top_stocks']) <= 3
    assert 'theme_sentiment' in result
    assert 'recommendation' in result

def test_analyze_theme_with_backtest():
    """백테스트 포함 통합 테스트"""
    result = ThemeFactorIntegrator.analyze_theme(
        theme="semiconductor",
        top_n=2,
        include_backtest=True,
        market="US",
        backtest_start="2024-01-01",
        backtest_end="2024-06-30"
    )

    assert len(result['top_stocks']) <= 2
    for stock in result['top_stocks']:
        assert 'backtest' in stock
        assert 'total_return' in stock['backtest'] or 'error' in stock['backtest']

def test_analyze_theme_error_handling():
    """에러 처리 테스트"""
    result = ThemeFactorIntegrator.analyze_theme(
        theme="nonexistent_theme_xyz",
        top_n=5,
        market="US"
    )

    assert 'error' in result or result['total_candidates'] == 0
```

#### 8.2.3 MCP Tool Tests

```python
def test_mcp_tool_theme_analyze():
    """MCP 도구 테스트"""
    import asyncio

    result = asyncio.run(theme_analyze_with_factors(
        theme="AI",
        top_n=3,
        include_backtest=False
    ))

    assert 'theme' in result
    assert 'top_stocks' in result

def test_mcp_tool_error():
    """MCP 도구 에러 테스트"""
    import asyncio

    result = asyncio.run(theme_analyze_with_factors(
        theme="invalid_theme",
        top_n=5
    ))

    assert 'error' in result or result.get('total_candidates', 0) == 0
```

### 8.3 Claude Desktop 실전 테스트

**테스트 시나리오**:

1. **기본 테마 분석**
   ```
   User: "AI 테마에서 투자할 종목 5개 추천해줘"
   Expected: theme_analyze_with_factors("AI", top_n=5)
   Verify: 5개 종목 + 팩터 점수 + 추천 등급
   ```

2. **백테스트 포함**
   ```
   User: "반도체 테마 상위 3개 종목을 백테스트 포함해서 분석해줘"
   Expected: theme_analyze_with_factors("semiconductor", top_n=3, include_backtest=True)
   Verify: 3개 종목 + 백테스트 수익률
   ```

3. **에러 처리**
   ```
   User: "존재하지 않는 테마로 분석해줘"
   Expected: 에러 메시지 + 대체 제안
   ```

---

## 9. 구현 순서

### 9.1 Week 1: Core Integration (High Priority)

**목표**: 기본 통합 기능 구현

#### Day 1-2: ThemeFactorIntegrator 클래스 생성

1. **파일 생성**
   - `mcp_server/tools/theme_factor_integrator.py`
   - 클래스 구조 + 메서드 스텁

2. **analyze_theme() 구현**
   - propose_tickers 호출
   - rank_theme_stocks 호출
   - 결과 포맷팅

3. **rank_theme_stocks() 구현**
   - FactorAggregator.rank_stocks 래핑
   - 에러 필터링

#### Day 3-4: MCP Tool 추가

1. **mcp_app.py 수정**
   - theme_analyze_with_factors() 도구 추가
   - 파라미터 검증
   - 에러 처리

2. **통합 테스트**
   - test_phase3_week1.py 작성
   - Claude Desktop 테스트

#### Day 5: Week 1 검증

1. **Unit Tests 실행**
2. **Integration Tests 실행**
3. **Claude Desktop 실전 테스트**
4. **Week 1 리포트 작성**

### 9.2 Week 2: Backtest Integration (Medium Priority)

**목표**: 백테스트 자동 실행

#### Day 1-2: enrich_with_backtest() 구현

1. **백테스트 로직 추가**
   - BacktestEngine.run_backtest 호출
   - 주요 지표 추출
   - 에러 처리

2. **analyze_theme() 수정**
   - include_backtest 파라미터 처리
   - enrich_with_backtest 호출

#### Day 3-4: 백테스트 통합 테스트

1. **test_phase3_week2.py 작성**
2. **백테스트 성능 측정**
3. **에러 케이스 테스트**

#### Day 5: Week 2 검증

### 9.3 Week 3: Sentiment Enhancement (Medium Priority)

**목표**: 감성 분석 기반 테마 추천 강화

#### Day 1-2: get_theme_sentiment() 구현

1. **뉴스 수집**
   - search_news 호출
   - 감성 분석

2. **트렌드 판단 로직**
   - 뉴스량 + 감성 점수

#### Day 3-4: generate_recommendation() 구현

1. **추천 로직**
   - 팩터 점수 + 백테스트 + 감성
   - 추천 텍스트 생성

2. **analyze_theme() 통합**

#### Day 5: Week 3 검증

### 9.4 Week 4: Optimization (Low Priority)

**목표**: 성능 최적화 + 캐싱

#### Day 1-3: Redis 캐싱 레이어

1. **cache_layer.py 생성**
   - Redis 연결
   - 캐시 키 설계
   - TTL 설정

2. **팩터 캐싱 통합**
   - FinancialFactors에 캐싱 추가
   - SentimentFactors에 캐싱 추가

#### Day 4-5: 최적화 검증

1. **성능 측정**
   - Before/After 비교
   - 응답 시간 확인

2. **Phase 3 통합 테스트**
3. **Phase 3 완료 리포트**

---

## 10. 예상 결과

### 10.1 성공 기준

1. ✅ theme_analyze_with_factors() 도구 작동
2. ✅ "AI 테마 추천" → 상위 5개 종목 성공
3. ✅ 팩터 점수 정렬 정확도 95%+
4. ✅ 백테스트 통합 작동 (optional)
5. ✅ 응답 시간 5초 이내
6. ✅ Claude Desktop 실전 테스트 통과

### 10.2 Phase 3 완료 후 기대 효과

**Before (Phase 2)**:
- 테마 추천: 4단계 (propose_themes → propose_tickers → comprehensive_analyze → backtest_strategy)
- 사용자 작업 시간: ~5분

**After (Phase 3)**:
- 테마 추천: 1단계 (theme_analyze_with_factors)
- 사용자 작업 시간: ~30초
- **90% 단축** 🚀

---

**설계 작성자**: Claude Sonnet 4.5
**작성 완료일**: 2026-02-27 18:15 KST
**다음 단계**: Phase 3 Week 1 구현 시작
