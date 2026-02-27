# Phase 3 설치 가이드

## Phase 3 Week 1 구현 완료

### ✅ 구현된 파일

1. **`mcp_server/tools/theme_factor_integrator.py`** (500+ lines)
   - ThemeFactorIntegrator 클래스
   - analyze_theme() - 통합 분석
   - get_theme_sentiment() - 테마 감성 분석
   - rank_theme_stocks() - 팩터 랭킹
   - enrich_with_backtest() - 백테스트 추가
   - generate_recommendation() - 투자 추천

2. **`mcp_server/mcp_app.py`** (수정)
   - theme_analyze_with_factors() MCP 도구 추가 (line 2334+)

3. **`test_phase3_week1.py`** (300+ lines)
   - 6개 테스트 케이스

## 🔧 설치 필요 의존성

현재 프록시 이슈로 일부 의존성이 설치되지 않았습니다.

### 필수 의존성

```bash
pip install feedparser>=6.0.11
pip install vaderSentiment>=3.3.2
```

### 전체 의존성 설치 (권장)

```bash
pip install -r requirements.txt
```

## 🧪 테스트 실행

의존성 설치 후:

```bash
python test_phase3_week1.py
```

### 예상 테스트 시간

- 테스트 1-4: 약 30-60초
- 테스트 5 (백테스트 포함): 약 1-2분
- 테스트 6: 약 5초

## 📱 Claude Desktop 테스트

MCP 서버 재시작 후 테스트:

```
사용자: "AI 테마에서 투자할 종목 5개 추천해줘"
→ theme_analyze_with_factors("AI", top_n=5)

사용자: "반도체 테마 상위 3개 종목을 백테스트 포함해서 분석해줘"
→ theme_analyze_with_factors("semiconductor", top_n=3, include_backtest=True)

사용자: "biotech 테마 분석"
→ theme_analyze_with_factors("biotech")
```

## 🔍 의존성 설치 문제 해결

### 프록시 이슈

만약 프록시 에러가 발생하면:

```bash
# 프록시 설정 해제
unset http_proxy
unset https_proxy

# 다시 설치
pip install feedparser vaderSentiment
```

### 권한 이슈

```bash
# 사용자 레벨 설치
pip install --user feedparser vaderSentiment
```

### 대체 방법

```bash
# conda 사용 (만약 사용 가능하면)
conda install -c conda-forge feedparser
pip install vaderSentiment
```

## 📊 구현 상태

### Week 1: Core Integration ✅ 구현 완료
- [x] ThemeFactorIntegrator 클래스
- [x] theme_analyze_with_factors() MCP 도구
- [x] 테스트 파일
- [ ] 의존성 설치 (보류 - 프록시 이슈)
- [ ] 테스트 실행 검증

### Week 2-4: 보류
- Week 2: Backtest Integration
- Week 3: Sentiment Enhancement
- Week 4: Caching Layer

## 🎯 다음 단계

1. **의존성 설치**
   ```bash
   pip install feedparser vaderSentiment
   ```

2. **테스트 실행**
   ```bash
   python test_phase3_week1.py
   ```

3. **MCP 서버 재시작**
   - Claude Desktop 재시작
   - 또는 MCP 서버 프로세스 재시작

4. **Claude Desktop 실전 테스트**
   - "AI 테마 추천해줘"
   - "반도체 테마 분석해줘"

5. **Week 1 완료 확인 후 Week 2 진행**

## 💡 참고

- Phase 3 계획: `docs/01-plan/features/phase3-theme-factor-integration.plan.md`
- Phase 3 설계: `docs/02-design/features/phase3-theme-factor-integration.design.md`
- 기존 interaction.py, factor_aggregator.py는 수정 없이 재사용
