# 03. Stock Analysis & Evaluation Algorithms

This document details the core logic used by the Strategy Engine to evaluate US stocks and execute trades.

## 1. Technical Indicators (Momentum & Trend)

### 1.1 Trend-Following Logic
- **EMA Crossover**: 50-day and 200-day EMA crossover (Golden Cross / Death Cross) for macro trend detection.
- **SuperTrend**: Dynamic ATR-based indicator for setting trailing stop-losses.
- **ADX (Average Directional Index)**: Filtering out sideways markets (Strength > 25 indicates a strong trend).

### 1.2 Volatility & Reversal
- **Bollinger Bands**: Identifying mean reversion opportunities when prices touch extreme bands.
- **RSI (Relative Strength Index)**: Standard 14-period RSI to detect overbought (>70) or oversold (<30) conditions.
- **MACD (Moving Average Convergence Divergence)**: Histograms to detect momentum shifts before price action conforms.

## 2. Fundamental & Macro Evaluation

### 2.1 Quality Metrics
- **P/E & PEG Ratios**: Comparative valuation within the same sector.
- **Divergence Ratio**: `(Net Income - Operating Cash Flow) / Total Assets`. Detects "accounting tricks" or poor profit quality.
- **Free Cash Flow (FCF) Yield**: Priority metric for long-term "Buy" signals.

### 2.2 Macro-Liquidity indicators (The "Fed" Overlay)
- **Net Liquidity Proxy**: Tracking the Fed Balance Sheet and TGA (Treasury General Account) to predict overall market "Beta" direction.
- **CPI & Interest Rate Sentiment**: Using the AI Agent to parse FOMC minutes and predict rate-cut/hike impacts on growth stocks.

## 3. Portfolio Evaluation & Risk Metrics

To refine the automated trading, the following metrics are calculated in real-time:

| Metric | Formula / Definition | Purpose |
| :--- | :--- | :--- |
| **Sharpe Ratio** | (Return - RiskFreeRate) / StdDev | Evaluates return per unit of risk. |
| **Sortino Ratio** | (Return - RiskFreeRate) / DownsideDev | Focuses purely on harmful volatility. |
| **Max Drawdown** | (Peak - Trough) / Peak | Measures the worst-case loss in a period. |
| **Profit Factor** | Gross Profit / Gross Loss | Overall effectiveness of the strategy. |

## 4. Automation Logic: Execution Pillars
1.  **Pre-Trade**: Check volatility (ATR) to determine position size (Risk parity).
2.  **In-Trade**: Apply "Time-Stop" (exit if trade stays flat for X days) and "Price-Stop".
3.  **Post-Trade**: Sentiment analysis on the exit reason to feed back into the AI loop.
