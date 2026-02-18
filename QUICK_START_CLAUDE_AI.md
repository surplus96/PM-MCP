# 🚀 Claude.ai 연동 빠른 시작 가이드

## 📌 준비 완료!

PM-MCP를 Claude.ai 웹 서비스에 연동하기 위한 모든 파일이 준비되었습니다.

---

## ⚡ 가장 빠른 방법 (Localtunnel)

### 1단계: 서버 시작

WSL Ubuntu 터미널을 열고:

```bash
cd /home/surplus96/projects/PM-MCP
bash start_with_localtunnel.sh
```

### 2단계: 공개 URL 확인

다음과 같은 출력이 나타납니다:

```
your url is: https://random-words-1234.loca.lt
```

### 3단계: Claude.ai에 연결

1. https://claude.ai 접속
2. 설정 → Integrations 또는 Custom MCP
3. 다음 정보 입력:
   - **Server Name**: PM-MCP
   - **Server URL**: `https://random-words-1234.loca.lt/sse`
   - (⚠️ URL 끝에 `/sse` 필수!)

### 4단계: 테스트

Claude.ai에서 테스트:

```
AAPL 주식의 최근 가격을 가져와줘
```

---

## 🔧 다른 방법

### 방법 A: ngrok (더 안정적, 계정 필요)

```bash
# 1. ngrok 설치
bash setup_ngrok.sh

# 2. ngrok 인증 (https://ngrok.com 가입 후)
ngrok config add-authtoken YOUR_TOKEN

# 3. 서버 시작
bash start_with_ngrok.sh
```

ngrok URL 예시: `https://abc123.ngrok-free.app/sse`

### 방법 B: 수동 실행 (디버깅용)

**Terminal 1:**
```bash
cd /home/surplus96/projects/PM-MCP
source .venv/bin/activate
python -m uvicorn mcp_server.mcp_app_http:app --host 0.0.0.0 --port 8010
```

**Terminal 2:**
```bash
npx localtunnel --port 8010
```

---

## 🎯 주요 기능 테스트

Claude.ai 연결 후 다음 명령을 시도해보세요:

### 시장 데이터
```
AAPL, MSFT, GOOGL의 최근 1개월 가격 추이를 차트로 보여줘
```

### 뉴스 분석
```
AI 관련 최근 뉴스 5개를 요약하고 감성 분석해줘
```

### 포트폴리오 분석
```
내 포트폴리오 [AAPL, MSFT, NVDA]를 종합 분석해줘
```

### 종목 비교
```
AAPL과 MSFT를 비교 분석해줘
```

### 기술적 분석
```
TSLA의 RSI, MACD, 볼린저 밴드를 분석해줘
```

---

## 🛠️ 문제 해결

### "Connection refused" 오류
```bash
# 서버가 실행 중인지 확인
ps aux | grep uvicorn

# 필요시 종료 후 재시작
pkill -f uvicorn
bash start_with_localtunnel.sh
```

### localtunnel IP 차단
```bash
# 커스텀 서브도메인으로 재시도
lt --port 8010 --subdomain my-pm-mcp
```

또는 ngrok 사용으로 전환

### Claude.ai에서 도구가 안 보임
- URL 끝에 `/sse`가 있는지 확인
- 터널 URL이 유효한지 확인: `curl YOUR_URL/sse`
- 서버 로그 확인: `cat mcp_server.log`

---

## 📚 더 자세한 정보

- 전체 가이드: `CLAUDE_AI_INTEGRATION.md`
- MCP 도구 목록: 87개 도구 사용 가능
- API 문서: README.md 참조

---

## 💡 팁

1. **터널 유지**: 터미널 창을 닫으면 터널이 종료됩니다
2. **로그 확인**: 문제 발생 시 `mcp_server.log` 확인
3. **ngrok UI**: ngrok 사용 시 http://localhost:4040 에서 요청 모니터링
4. **보안**: 터널 URL을 공개 저장소에 올리지 마세요

---

## ✅ 체크리스트

- [ ] WSL Ubuntu 실행 확인
- [ ] PM-MCP 디렉토리로 이동
- [ ] `start_with_localtunnel.sh` 실행
- [ ] 공개 URL 복사
- [ ] Claude.ai에 URL 등록 (끝에 `/sse` 추가!)
- [ ] Claude.ai에서 테스트 명령 실행

---

🎉 **설정 완료! 이제 Claude.ai에서 PM-MCP를 사용할 수 있습니다!**
