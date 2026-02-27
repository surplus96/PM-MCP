"""재무 팩터 계산 모듈 (20개)

Phase 2-1: 재무 지표 확장
- 수익성 지표 (5개): ROE, ROA, ROIC, Operating Margin, Net Margin
- 재무 건전성 지표 (5개): Debt to Equity, Current Ratio, Quick Ratio, Interest Coverage, Debt to Asset
- 효율성 지표 (5개): Asset Turnover, Inventory Turnover, Receivables Turnover, Working Capital Turnover, FCF to Sales
- 배당 지표 (3개): Dividend Yield, Payout Ratio, Dividend Growth
- 성장성 지표 (2개): Revenue Growth, EPS Growth
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging
import yfinance as yf
from .yf_utils import normalize_ticker_multi_market

logger = logging.getLogger(__name__)


class FinancialFactors:
    """재무 팩터 계산 클래스 (20개)"""

    # ============================================================
    # 그룹 1: 수익성 지표 (5개)
    # ============================================================
    @staticmethod
    def calculate_profitability(ticker: str, market: str = "US") -> Dict[str, float]:
        """수익성 지표 계산

        Args:
            ticker: 종목 코드
            market: 시장 구분 ("US", "KR")

        Returns:
            {
                'ROE': float,           # Return on Equity
                'ROA': float,           # Return on Assets
                'ROIC': float,          # Return on Invested Capital
                'Operating_Margin': float,
                'Net_Margin': float
            }
        """
        try:
            # 티커 정규화
            normalized_ticker = normalize_ticker_multi_market(ticker, market)
            stock = yf.Ticker(normalized_ticker)
            info = stock.info

            # ROE (Return on Equity)
            roe = info.get('returnOnEquity', np.nan)

            # ROA (Return on Assets)
            roa = info.get('returnOnAssets', np.nan)

            # ROIC (Return on Invested Capital)
            # ROIC = NOPAT / Invested Capital
            try:
                financials = stock.financials
                balance = stock.balance_sheet

                if financials.empty or balance.empty:
                    roic = np.nan
                else:
                    # NOPAT = Operating Income * (1 - Tax Rate)
                    if 'Operating Income' in financials.index:
                        operating_income = financials.loc['Operating Income'].iloc[0]
                    elif 'EBIT' in financials.index:
                        operating_income = financials.loc['EBIT'].iloc[0]
                    else:
                        operating_income = None

                    tax_rate = info.get('effectiveTaxRate', 0.21)  # 기본 21%

                    if operating_income is not None and not pd.isna(operating_income):
                        nopat = operating_income * (1 - tax_rate)

                        # Invested Capital = Total Equity + Total Debt - Cash
                        total_equity = balance.loc['Stockholders Equity'].iloc[0] if 'Stockholders Equity' in balance.index else 0
                        total_debt = balance.loc['Total Debt'].iloc[0] if 'Total Debt' in balance.index else 0
                        cash = balance.loc['Cash'].iloc[0] if 'Cash' in balance.index else 0

                        invested_capital = total_equity + total_debt - cash

                        if invested_capital > 0:
                            roic = nopat / invested_capital
                        else:
                            roic = np.nan
                    else:
                        roic = np.nan

            except Exception as e:
                logger.debug(f"ROIC calculation failed for {ticker}: {e}")
                roic = np.nan

            # Operating Margin
            operating_margin = info.get('operatingMargins', np.nan)

            # Net Margin
            net_margin = info.get('profitMargins', np.nan)

            return {
                'ROE': roe,
                'ROA': roa,
                'ROIC': roic,
                'Operating_Margin': operating_margin,
                'Net_Margin': net_margin
            }

        except Exception as e:
            logger.warning(f"Profitability calculation failed for {ticker}: {e}")
            return {}

    # ============================================================
    # 그룹 2: 재무 건전성 지표 (5개)
    # ============================================================
    @staticmethod
    def calculate_financial_health(ticker: str, market: str = "US") -> Dict[str, float]:
        """재무 건전성 지표 계산

        Returns:
            {
                'Debt_to_Equity': float,
                'Current_Ratio': float,
                'Quick_Ratio': float,
                'Interest_Coverage': float,
                'Debt_to_Asset': float
            }
        """
        try:
            normalized_ticker = normalize_ticker_multi_market(ticker, market)
            stock = yf.Ticker(normalized_ticker)
            info = stock.info
            balance = stock.balance_sheet
            financials = stock.financials

            # Debt to Equity
            debt_to_equity = info.get('debtToEquity', np.nan)
            if not pd.isna(debt_to_equity):
                debt_to_equity = debt_to_equity / 100  # yfinance는 %로 반환

            # Current Ratio
            current_ratio = info.get('currentRatio', np.nan)

            # Quick Ratio
            quick_ratio = info.get('quickRatio', np.nan)

            # Interest Coverage = EBIT / Interest Expense
            try:
                if not financials.empty:
                    ebit = financials.loc['EBIT'].iloc[0] if 'EBIT' in financials.index else np.nan
                    interest_expense = financials.loc['Interest Expense'].iloc[0] if 'Interest Expense' in financials.index else np.nan

                    if not pd.isna(ebit) and not pd.isna(interest_expense) and interest_expense != 0:
                        interest_coverage = abs(ebit / interest_expense)
                    else:
                        interest_coverage = np.nan
                else:
                    interest_coverage = np.nan
            except Exception:
                interest_coverage = np.nan

            # Debt to Asset = Total Debt / Total Assets
            try:
                if not balance.empty:
                    total_debt = balance.loc['Total Debt'].iloc[0] if 'Total Debt' in balance.index else 0
                    total_assets = balance.loc['Total Assets'].iloc[0] if 'Total Assets' in balance.index else 0

                    if total_assets > 0:
                        debt_to_asset = total_debt / total_assets
                    else:
                        debt_to_asset = np.nan
                else:
                    debt_to_asset = np.nan
            except Exception:
                debt_to_asset = np.nan

            return {
                'Debt_to_Equity': debt_to_equity,
                'Current_Ratio': current_ratio,
                'Quick_Ratio': quick_ratio,
                'Interest_Coverage': interest_coverage,
                'Debt_to_Asset': debt_to_asset
            }

        except Exception as e:
            logger.warning(f"Financial health calculation failed for {ticker}: {e}")
            return {}

    # ============================================================
    # 그룹 3: 효율성 지표 (5개)
    # ============================================================
    @staticmethod
    def calculate_efficiency(ticker: str, market: str = "US") -> Dict[str, float]:
        """효율성 지표 계산

        Returns:
            {
                'Asset_Turnover': float,
                'Inventory_Turnover': float,
                'Receivables_Turnover': float,
                'Working_Capital_Turnover': float,
                'FCF_to_Sales': float
            }
        """
        try:
            normalized_ticker = normalize_ticker_multi_market(ticker, market)
            stock = yf.Ticker(normalized_ticker)
            info = stock.info
            financials = stock.financials
            balance = stock.balance_sheet
            cashflow = stock.cashflow

            # Asset Turnover = Revenue / Average Total Assets
            try:
                if not financials.empty and not balance.empty:
                    revenue = financials.loc['Total Revenue'].iloc[0] if 'Total Revenue' in financials.index else np.nan
                    total_assets = balance.loc['Total Assets'].iloc[0] if 'Total Assets' in balance.index else np.nan

                    if not pd.isna(revenue) and not pd.isna(total_assets) and total_assets > 0:
                        asset_turnover = revenue / total_assets
                    else:
                        asset_turnover = np.nan
                else:
                    asset_turnover = np.nan
            except Exception:
                asset_turnover = np.nan

            # Inventory Turnover = Cost of Revenue / Average Inventory
            try:
                if not financials.empty and not balance.empty:
                    cogs = financials.loc['Cost Of Revenue'].iloc[0] if 'Cost Of Revenue' in financials.index else np.nan
                    inventory = balance.loc['Inventory'].iloc[0] if 'Inventory' in balance.index else np.nan

                    if not pd.isna(cogs) and not pd.isna(inventory) and inventory > 0:
                        inventory_turnover = cogs / inventory
                    else:
                        inventory_turnover = np.nan
                else:
                    inventory_turnover = np.nan
            except Exception:
                inventory_turnover = np.nan

            # Receivables Turnover = Revenue / Average Receivables
            try:
                if not financials.empty and not balance.empty:
                    revenue = financials.loc['Total Revenue'].iloc[0] if 'Total Revenue' in financials.index else np.nan
                    receivables = balance.loc['Accounts Receivable'].iloc[0] if 'Accounts Receivable' in balance.index else np.nan

                    if not pd.isna(revenue) and not pd.isna(receivables) and receivables > 0:
                        receivables_turnover = revenue / receivables
                    else:
                        receivables_turnover = np.nan
                else:
                    receivables_turnover = np.nan
            except Exception:
                receivables_turnover = np.nan

            # Working Capital Turnover = Revenue / Working Capital
            try:
                if not financials.empty and not balance.empty:
                    revenue = financials.loc['Total Revenue'].iloc[0] if 'Total Revenue' in financials.index else np.nan
                    current_assets = balance.loc['Current Assets'].iloc[0] if 'Current Assets' in balance.index else 0
                    current_liabilities = balance.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in balance.index else 0
                    working_capital = current_assets - current_liabilities

                    if not pd.isna(revenue) and working_capital > 0:
                        wc_turnover = revenue / working_capital
                    else:
                        wc_turnover = np.nan
                else:
                    wc_turnover = np.nan
            except Exception:
                wc_turnover = np.nan

            # FCF to Sales = Free Cash Flow / Revenue
            try:
                if not cashflow.empty and not financials.empty:
                    fcf = cashflow.loc['Free Cash Flow'].iloc[0] if 'Free Cash Flow' in cashflow.index else np.nan
                    revenue = financials.loc['Total Revenue'].iloc[0] if 'Total Revenue' in financials.index else np.nan

                    if not pd.isna(fcf) and not pd.isna(revenue) and revenue > 0:
                        fcf_to_sales = fcf / revenue
                    else:
                        fcf_to_sales = np.nan
                else:
                    fcf_to_sales = np.nan
            except Exception:
                fcf_to_sales = np.nan

            return {
                'Asset_Turnover': asset_turnover,
                'Inventory_Turnover': inventory_turnover,
                'Receivables_Turnover': receivables_turnover,
                'Working_Capital_Turnover': wc_turnover,
                'FCF_to_Sales': fcf_to_sales
            }

        except Exception as e:
            logger.warning(f"Efficiency calculation failed for {ticker}: {e}")
            return {}

    # ============================================================
    # 그룹 4: 배당 지표 (3개)
    # ============================================================
    @staticmethod
    def calculate_dividend(ticker: str, market: str = "US") -> Dict[str, float]:
        """배당 지표 계산

        Returns:
            {
                'Dividend_Yield': float,
                'Payout_Ratio': float,
                'Dividend_Growth': float
            }
        """
        try:
            normalized_ticker = normalize_ticker_multi_market(ticker, market)
            stock = yf.Ticker(normalized_ticker)
            info = stock.info

            # Dividend Yield
            dividend_yield = info.get('dividendYield', np.nan)

            # Payout Ratio
            payout_ratio = info.get('payoutRatio', np.nan)

            # Dividend Growth (5년 평균)
            dividend_growth = info.get('fiveYearAvgDividendYield', np.nan)

            # Dividend Growth 계산 (직접)
            try:
                dividends = stock.dividends
                if not dividends.empty and len(dividends) >= 2:
                    # 최근 연간 배당 vs 1년 전 배당
                    recent_year_div = dividends.last('365D').sum()
                    prev_year_div = dividends.iloc[:-365].last('365D').sum() if len(dividends) > 365 else 0

                    if prev_year_div > 0 and recent_year_div > 0:
                        div_growth = (recent_year_div - prev_year_div) / prev_year_div
                    else:
                        div_growth = np.nan
                else:
                    div_growth = np.nan
            except Exception:
                div_growth = np.nan

            # fiveYearAvgDividendYield가 없으면 직접 계산한 값 사용
            if pd.isna(dividend_growth):
                dividend_growth = div_growth

            return {
                'Dividend_Yield': dividend_yield,
                'Payout_Ratio': payout_ratio,
                'Dividend_Growth': dividend_growth
            }

        except Exception as e:
            logger.warning(f"Dividend calculation failed for {ticker}: {e}")
            return {}

    # ============================================================
    # 그룹 5: 성장성 지표 (2개)
    # ============================================================
    @staticmethod
    def calculate_growth(ticker: str, market: str = "US") -> Dict[str, float]:
        """성장성 지표 계산

        Returns:
            {
                'Revenue_Growth': float,
                'EPS_Growth': float
            }
        """
        try:
            normalized_ticker = normalize_ticker_multi_market(ticker, market)
            stock = yf.Ticker(normalized_ticker)
            info = stock.info
            financials = stock.financials

            # Revenue Growth (YoY)
            revenue_growth = info.get('revenueGrowth', np.nan)

            # 직접 계산
            if pd.isna(revenue_growth) and not financials.empty:
                try:
                    if 'Total Revenue' in financials.index and len(financials.columns) >= 2:
                        recent_revenue = financials.loc['Total Revenue'].iloc[0]
                        prev_revenue = financials.loc['Total Revenue'].iloc[1]

                        if not pd.isna(recent_revenue) and not pd.isna(prev_revenue) and prev_revenue > 0:
                            revenue_growth = (recent_revenue - prev_revenue) / prev_revenue
                except Exception:
                    pass

            # EPS Growth (YoY)
            earnings_growth = info.get('earningsGrowth', np.nan)

            # 직접 계산
            if pd.isna(earnings_growth):
                try:
                    earnings_history = stock.earnings
                    if not earnings_history.empty and len(earnings_history) >= 2:
                        recent_eps = earnings_history['Earnings'].iloc[-1]
                        prev_eps = earnings_history['Earnings'].iloc[-2]

                        if not pd.isna(recent_eps) and not pd.isna(prev_eps) and prev_eps != 0:
                            earnings_growth = (recent_eps - prev_eps) / abs(prev_eps)
                except Exception:
                    pass

            return {
                'Revenue_Growth': revenue_growth,
                'EPS_Growth': earnings_growth
            }

        except Exception as e:
            logger.warning(f"Growth calculation failed for {ticker}: {e}")
            return {}

    # ============================================================
    # 통합 함수
    # ============================================================
    @staticmethod
    def calculate_all(ticker: str, market: str = "US") -> Dict[str, float]:
        """20개 재무 팩터 통합 계산

        Args:
            ticker: 종목 코드
            market: 시장 구분 ("US", "KR")

        Returns:
            재무 팩터 딕셔너리 (NaN 값 제거)
        """
        factors = {}

        try:
            # 1. 수익성 (5개)
            profitability = FinancialFactors.calculate_profitability(ticker, market)
            factors.update(profitability)

            # 2. 재무 건전성 (5개)
            health = FinancialFactors.calculate_financial_health(ticker, market)
            factors.update(health)

            # 3. 효율성 (5개) - Week 2
            efficiency = FinancialFactors.calculate_efficiency(ticker, market)
            factors.update(efficiency)

            # 4. 배당 (3개) - Week 2
            dividend = FinancialFactors.calculate_dividend(ticker, market)
            factors.update(dividend)

            # 5. 성장성 (2개) - Week 2
            growth = FinancialFactors.calculate_growth(ticker, market)
            factors.update(growth)

        except Exception as e:
            logger.error(f"Failed to calculate financial factors for {ticker}: {e}")

        # NaN 값 제거
        factors = {k: v for k, v in factors.items() if not pd.isna(v)}

        logger.info(f"Calculated {len(factors)}/20 financial factors for {ticker}")
        return factors

    @staticmethod
    def get_factor_interpretation(factors: Dict[str, float]) -> Dict[str, str]:
        """재무 팩터 해석

        Args:
            factors: 계산된 재무 팩터

        Returns:
            팩터별 해석 딕셔너리
        """
        interpretation = {}

        # ROE 해석
        if 'ROE' in factors:
            roe = factors['ROE'] * 100  # %로 변환
            if roe > 15:
                interpretation['ROE'] = f"우수한 자기자본 수익률 ({roe:.1f}%)"
            elif roe > 10:
                interpretation['ROE'] = f"양호한 자기자본 수익률 ({roe:.1f}%)"
            elif roe > 0:
                interpretation['ROE'] = f"낮은 자기자본 수익률 ({roe:.1f}%)"
            else:
                interpretation['ROE'] = f"손실 ({roe:.1f}%)"

        # ROA 해석
        if 'ROA' in factors:
            roa = factors['ROA'] * 100
            if roa > 10:
                interpretation['ROA'] = f"우수한 자산 수익률 ({roa:.1f}%)"
            elif roa > 5:
                interpretation['ROA'] = f"양호한 자산 수익률 ({roa:.1f}%)"
            else:
                interpretation['ROA'] = f"낮은 자산 수익률 ({roa:.1f}%)"

        # Debt to Equity 해석
        if 'Debt_to_Equity' in factors:
            de = factors['Debt_to_Equity']
            if de < 0.5:
                interpretation['Debt_to_Equity'] = f"매우 건전한 부채 수준 ({de:.2f})"
            elif de < 1.0:
                interpretation['Debt_to_Equity'] = f"건전한 부채 수준 ({de:.2f})"
            elif de < 2.0:
                interpretation['Debt_to_Equity'] = f"보통 부채 수준 ({de:.2f})"
            else:
                interpretation['Debt_to_Equity'] = f"높은 부채 수준 ({de:.2f})"

        # Current Ratio 해석
        if 'Current_Ratio' in factors:
            cr = factors['Current_Ratio']
            if cr > 2.0:
                interpretation['Current_Ratio'] = f"유동성 우수 ({cr:.2f})"
            elif cr > 1.5:
                interpretation['Current_Ratio'] = f"유동성 양호 ({cr:.2f})"
            elif cr > 1.0:
                interpretation['Current_Ratio'] = f"유동성 적정 ({cr:.2f})"
            else:
                interpretation['Current_Ratio'] = f"유동성 주의 ({cr:.2f})"

        # Operating Margin 해석
        if 'Operating_Margin' in factors:
            om = factors['Operating_Margin'] * 100
            if om > 20:
                interpretation['Operating_Margin'] = f"매우 높은 영업이익률 ({om:.1f}%)"
            elif om > 10:
                interpretation['Operating_Margin'] = f"양호한 영업이익률 ({om:.1f}%)"
            elif om > 0:
                interpretation['Operating_Margin'] = f"낮은 영업이익률 ({om:.1f}%)"
            else:
                interpretation['Operating_Margin'] = f"영업손실 ({om:.1f}%)"

        # Asset Turnover 해석 (효율성)
        if 'Asset_Turnover' in factors:
            at = factors['Asset_Turnover']
            if at > 1.5:
                interpretation['Asset_Turnover'] = f"매우 높은 자산 회전율 ({at:.2f})"
            elif at > 1.0:
                interpretation['Asset_Turnover'] = f"양호한 자산 회전율 ({at:.2f})"
            elif at > 0.5:
                interpretation['Asset_Turnover'] = f"보통 자산 회전율 ({at:.2f})"
            else:
                interpretation['Asset_Turnover'] = f"낮은 자산 회전율 ({at:.2f})"

        # Inventory Turnover 해석
        if 'Inventory_Turnover' in factors:
            it = factors['Inventory_Turnover']
            if it > 10:
                interpretation['Inventory_Turnover'] = f"매우 빠른 재고 회전 ({it:.1f})"
            elif it > 5:
                interpretation['Inventory_Turnover'] = f"양호한 재고 회전 ({it:.1f})"
            elif it > 2:
                interpretation['Inventory_Turnover'] = f"보통 재고 회전 ({it:.1f})"
            else:
                interpretation['Inventory_Turnover'] = f"느린 재고 회전 ({it:.1f})"

        # FCF to Sales 해석
        if 'FCF_to_Sales' in factors:
            fcf = factors['FCF_to_Sales'] * 100
            if fcf > 15:
                interpretation['FCF_to_Sales'] = f"매우 높은 현금 창출력 ({fcf:.1f}%)"
            elif fcf > 10:
                interpretation['FCF_to_Sales'] = f"양호한 현금 창출력 ({fcf:.1f}%)"
            elif fcf > 5:
                interpretation['FCF_to_Sales'] = f"보통 현금 창출력 ({fcf:.1f}%)"
            elif fcf > 0:
                interpretation['FCF_to_Sales'] = f"낮은 현금 창출력 ({fcf:.1f}%)"
            else:
                interpretation['FCF_to_Sales'] = f"현금 흐름 부족 ({fcf:.1f}%)"

        # Dividend Yield 해석
        if 'Dividend_Yield' in factors:
            dy = factors['Dividend_Yield'] * 100
            if dy > 4:
                interpretation['Dividend_Yield'] = f"고배당주 ({dy:.2f}%)"
            elif dy > 2:
                interpretation['Dividend_Yield'] = f"배당 적정 ({dy:.2f}%)"
            elif dy > 0:
                interpretation['Dividend_Yield'] = f"저배당 ({dy:.2f}%)"
            else:
                interpretation['Dividend_Yield'] = "무배당"

        # Payout Ratio 해석
        if 'Payout_Ratio' in factors:
            pr = factors['Payout_Ratio'] * 100
            if pr > 80:
                interpretation['Payout_Ratio'] = f"높은 배당성향 ({pr:.1f}%)"
            elif pr > 40:
                interpretation['Payout_Ratio'] = f"적정 배당성향 ({pr:.1f}%)"
            elif pr > 0:
                interpretation['Payout_Ratio'] = f"낮은 배당성향 ({pr:.1f}%)"

        # Revenue Growth 해석
        if 'Revenue_Growth' in factors:
            rg = factors['Revenue_Growth'] * 100
            if rg > 20:
                interpretation['Revenue_Growth'] = f"매우 빠른 매출 성장 ({rg:.1f}%)"
            elif rg > 10:
                interpretation['Revenue_Growth'] = f"빠른 매출 성장 ({rg:.1f}%)"
            elif rg > 5:
                interpretation['Revenue_Growth'] = f"안정적 매출 성장 ({rg:.1f}%)"
            elif rg > 0:
                interpretation['Revenue_Growth'] = f"느린 매출 성장 ({rg:.1f}%)"
            else:
                interpretation['Revenue_Growth'] = f"매출 감소 ({rg:.1f}%)"

        # EPS Growth 해석
        if 'EPS_Growth' in factors:
            eg = factors['EPS_Growth'] * 100
            if eg > 25:
                interpretation['EPS_Growth'] = f"매우 빠른 이익 성장 ({eg:.1f}%)"
            elif eg > 15:
                interpretation['EPS_Growth'] = f"빠른 이익 성장 ({eg:.1f}%)"
            elif eg > 5:
                interpretation['EPS_Growth'] = f"안정적 이익 성장 ({eg:.1f}%)"
            elif eg > 0:
                interpretation['EPS_Growth'] = f"느린 이익 성장 ({eg:.1f}%)"
            else:
                interpretation['EPS_Growth'] = f"이익 감소 ({eg:.1f}%)"

        return interpretation
