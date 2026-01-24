"""
Data Integration Layer
- Alpha Vantage + Finnhub + Yahoo Finance 통합
- 멀티소스 데이터 병합
- 신호 강도 분석
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from mcp_server.tools.cache_manager import cache_manager, TTL
from mcp_server.tools.alpha_vantage import (
    get_rsi, get_macd, get_bbands, get_technical_summary
)
from mcp_server.tools.finnhub_api import (
    get_company_news, get_insider_transactions,
    get_analyst_recommendations, get_basic_financials,
    get_finnhub_summary
)
from mcp_server.tools.market_data import get_prices


class DataIntegrator:
    """멀티소스 데이터 통합 클래스"""

    def __init__(self):
        self.sources = {
            "technical": "Alpha Vantage",
            "fundamental": "Finnhub",
            "price": "Yahoo Finance"
        }

    def get_comprehensive_analysis(self, symbol: str) -> Dict[str, Any]:
        """
        종합 분석 데이터 가져오기

        Args:
            symbol: 종목 심볼

        Returns:
            기술적/기본적/뉴스 종합 분석
        """
        cache_key = f"integrated_analysis_{symbol}"
        cached = cache_manager.get(cache_key)
        if cached:
            return cached

        results = {
            "symbol": symbol.upper(),
            "timestamp": datetime.now().isoformat(),
            "data_sources": self.sources
        }

        # 병렬로 데이터 수집
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._get_technical_data, symbol): "technical",
                executor.submit(self._get_fundamental_data, symbol): "fundamental",
                executor.submit(self._get_news_sentiment, symbol): "sentiment",
                executor.submit(self._get_price_data, symbol): "price"
            }

            for future in as_completed(futures):
                data_type = futures[future]
                try:
                    data = future.result()
                    results[data_type] = data
                except Exception as e:
                    results[data_type] = {"error": str(e)}

        # 종합 신호 계산
        results["composite_signal"] = self._calculate_composite_signal(results)

        cache_manager.set(cache_key, results, ttl=TTL.NEWS)
        return results

    def _get_technical_data(self, symbol: str) -> Dict:
        """기술적 분석 데이터"""
        try:
            summary = get_technical_summary(symbol)
            return {
                "rsi": summary.get("indicators", {}).get("rsi", {}),
                "macd": summary.get("indicators", {}).get("macd", {}),
                "bbands": summary.get("indicators", {}).get("bbands", {}),
                "signals": summary.get("signals", []),
                "overall": summary.get("overall_signal", "N/A")
            }
        except Exception as e:
            return {"error": str(e), "overall": "N/A"}

    def _get_fundamental_data(self, symbol: str) -> Dict:
        """기본적 분석 데이터"""
        try:
            financials = get_basic_financials(symbol)
            analyst = get_analyst_recommendations(symbol)
            insider = get_insider_transactions(symbol)

            return {
                "valuation": financials.get("metrics", {}).get("valuation", {}),
                "profitability": financials.get("metrics", {}).get("profitability", {}),
                "growth": financials.get("metrics", {}).get("growth", {}),
                "scores": financials.get("scores", {}),
                "analyst_consensus": analyst.get("consensus", {}),
                "analyst_trend": analyst.get("trend", "N/A"),
                "insider_signal": insider.get("summary", {}).get("insider_signal", "N/A")
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_news_sentiment(self, symbol: str) -> Dict:
        """뉴스 감성 분석"""
        try:
            news = get_company_news(symbol)
            return {
                "count": news.get("total_count", 0),
                "sentiment": news.get("sentiment_summary", {}),
                "period": news.get("period", "")
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_price_data(self, symbol: str) -> Dict:
        """가격 데이터"""
        try:
            prices = get_prices(symbol, period="3mo")

            if prices and len(prices) > 0:
                latest = prices[-1]
                first = prices[0]

                # 수익률 계산
                if first.get("close") and latest.get("close"):
                    returns_3m = ((latest["close"] - first["close"]) / first["close"]) * 100
                else:
                    returns_3m = None

                # 변동성 계산
                closes = [p.get("close") for p in prices if p.get("close")]
                if len(closes) > 1:
                    import statistics
                    daily_returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                    volatility = statistics.stdev(daily_returns) * (252 ** 0.5) * 100  # 연환산
                else:
                    volatility = None

                return {
                    "latest_price": latest.get("close"),
                    "latest_date": latest.get("date"),
                    "returns_3m": round(returns_3m, 2) if returns_3m else None,
                    "volatility_annual": round(volatility, 2) if volatility else None,
                    "data_points": len(prices)
                }
            return {"error": "No price data"}
        except Exception as e:
            return {"error": str(e)}

    def _calculate_composite_signal(self, data: Dict) -> Dict:
        """종합 신호 계산"""
        signals = []
        weights = {
            "technical": 0.30,
            "fundamental": 0.35,
            "sentiment": 0.20,
            "momentum": 0.15
        }

        # 기술적 신호 (-1 to 1)
        tech = data.get("technical", {})
        tech_signal = tech.get("overall", "N/A")
        if tech_signal == "Bullish":
            signals.append(("Technical", 1.0, weights["technical"]))
        elif tech_signal == "Bearish":
            signals.append(("Technical", -1.0, weights["technical"]))
        elif tech_signal == "Neutral":
            signals.append(("Technical", 0.0, weights["technical"]))

        # 기본적 신호
        fund = data.get("fundamental", {})

        # 애널리스트 컨센서스
        consensus = fund.get("analyst_consensus", {}).get("consensus", "")
        if consensus in ["Strong Buy", "Buy"]:
            signals.append(("Analyst", 1.0 if "Strong" in consensus else 0.5, weights["fundamental"] * 0.5))
        elif consensus in ["Strong Sell", "Sell"]:
            signals.append(("Analyst", -1.0 if "Strong" in consensus else -0.5, weights["fundamental"] * 0.5))
        elif consensus == "Hold":
            signals.append(("Analyst", 0.0, weights["fundamental"] * 0.5))

        # 내부자 신호
        insider = fund.get("insider_signal", "")
        if "Buy" in insider:
            signals.append(("Insider", 0.5 if "Moderate" in insider else 1.0, weights["fundamental"] * 0.5))
        elif "Sell" in insider:
            signals.append(("Insider", -0.5 if "Moderate" in insider else -1.0, weights["fundamental"] * 0.5))

        # 뉴스 감성
        sentiment = data.get("sentiment", {}).get("sentiment", {})
        if sentiment:
            pos = sentiment.get("positive", 0)
            neg = sentiment.get("negative", 0)
            total = pos + neg + sentiment.get("neutral", 0)
            if total > 0:
                score = (pos - neg) / total
                signals.append(("News", score, weights["sentiment"]))

        # 모멘텀 (3개월 수익률 기반)
        price = data.get("price", {})
        returns_3m = price.get("returns_3m")
        if returns_3m is not None:
            # -30% ~ +30% 를 -1 ~ +1 로 매핑
            momentum_score = max(-1, min(1, returns_3m / 30))
            signals.append(("Momentum", momentum_score, weights["momentum"]))

        # 가중 평균 계산
        if signals:
            total_weight = sum(s[2] for s in signals)
            weighted_sum = sum(s[1] * s[2] for s in signals)
            composite_score = weighted_sum / total_weight if total_weight > 0 else 0

            if composite_score > 0.3:
                overall = "Bullish"
            elif composite_score < -0.3:
                overall = "Bearish"
            else:
                overall = "Neutral"

            return {
                "overall": overall,
                "score": round(composite_score, 3),
                "components": [
                    {"factor": s[0], "signal": s[1], "weight": s[2]}
                    for s in signals
                ],
                "confidence": round(total_weight, 2)
            }

        return {"overall": "Insufficient Data", "score": 0, "components": []}

    def compare_stocks(self, symbols: List[str]) -> Dict[str, Any]:
        """
        여러 종목 비교 분석

        Args:
            symbols: 종목 심볼 리스트

        Returns:
            비교 분석 결과
        """
        results = {
            "comparison_date": datetime.now().isoformat(),
            "stocks": []
        }

        # 병렬로 데이터 수집
        with ThreadPoolExecutor(max_workers=min(len(symbols), 5)) as executor:
            futures = {
                executor.submit(self.get_comprehensive_analysis, symbol): symbol
                for symbol in symbols
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    data = future.result()
                    results["stocks"].append({
                        "symbol": symbol.upper(),
                        "composite": data.get("composite_signal", {}),
                        "technical": data.get("technical", {}).get("overall", "N/A"),
                        "analyst": data.get("fundamental", {}).get("analyst_consensus", {}).get("consensus", "N/A"),
                        "insider": data.get("fundamental", {}).get("insider_signal", "N/A"),
                        "returns_3m": data.get("price", {}).get("returns_3m"),
                        "volatility": data.get("price", {}).get("volatility_annual")
                    })
                except Exception as e:
                    results["stocks"].append({
                        "symbol": symbol.upper(),
                        "error": str(e)
                    })

        # 점수 기준 정렬
        results["stocks"].sort(
            key=lambda x: x.get("composite", {}).get("score", -999),
            reverse=True
        )

        # 랭킹 추가
        for i, stock in enumerate(results["stocks"], 1):
            stock["rank"] = i

        return results

    def get_investment_signals(self, symbol: str) -> Dict[str, Any]:
        """
        투자 신호 요약 (의사결정 지원용)

        Args:
            symbol: 종목 심볼

        Returns:
            Buy/Hold/Sell 신호와 근거
        """
        analysis = self.get_comprehensive_analysis(symbol)
        composite = analysis.get("composite_signal", {})

        score = composite.get("score", 0)
        overall = composite.get("overall", "Neutral")

        # 의사결정 신호
        if score > 0.5:
            decision = "Strong Buy"
            confidence = "High"
        elif score > 0.2:
            decision = "Buy"
            confidence = "Moderate"
        elif score > -0.2:
            decision = "Hold"
            confidence = "Moderate" if abs(score) < 0.1 else "Low"
        elif score > -0.5:
            decision = "Sell"
            confidence = "Moderate"
        else:
            decision = "Strong Sell"
            confidence = "High"

        # 주요 근거 추출
        reasons = []
        components = composite.get("components", [])

        for comp in components:
            factor = comp.get("factor", "")
            signal = comp.get("signal", 0)

            if signal > 0.5:
                reasons.append(f"{factor}: Strong positive signal")
            elif signal > 0.2:
                reasons.append(f"{factor}: Positive signal")
            elif signal < -0.5:
                reasons.append(f"{factor}: Strong negative signal")
            elif signal < -0.2:
                reasons.append(f"{factor}: Negative signal")

        # 리스크 요소
        risks = []
        volatility = analysis.get("price", {}).get("volatility_annual")
        if volatility and volatility > 40:
            risks.append(f"High volatility ({volatility:.1f}% annual)")

        insider = analysis.get("fundamental", {}).get("insider_signal", "")
        if "Sell" in insider:
            risks.append("Insider selling activity detected")

        returns_3m = analysis.get("price", {}).get("returns_3m")
        if returns_3m and returns_3m < -20:
            risks.append(f"Significant price decline ({returns_3m:.1f}% in 3 months)")

        return {
            "symbol": symbol.upper(),
            "decision": decision,
            "confidence": confidence,
            "score": round(score, 3),
            "reasons": reasons[:5],  # 상위 5개
            "risks": risks,
            "analysis_date": datetime.now().isoformat(),
            "disclaimer": "This is not financial advice. Always do your own research."
        }


# 싱글톤 인스턴스
data_integrator = DataIntegrator()


# 편의 함수들
def get_stock_analysis(symbol: str) -> Dict[str, Any]:
    """종목 종합 분석"""
    return data_integrator.get_comprehensive_analysis(symbol)


def compare_stocks(symbols: List[str]) -> Dict[str, Any]:
    """종목 비교"""
    return data_integrator.compare_stocks(symbols)


def get_investment_signal(symbol: str) -> Dict[str, Any]:
    """투자 신호"""
    return data_integrator.get_investment_signals(symbol)
