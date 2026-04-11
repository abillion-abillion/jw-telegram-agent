# JW Telegram Agent

> Telegram에서 말로 지시 → Claude가 처리 → 결과 응답
> Railway 클라우드에서 24/7 운영

---

## 구조

```
진우님 Telegram 메시지
  ↓
Railway (FastAPI 서버, 24/7 상주)
  ↓
Claude API (AGENTS.md 컨텍스트 포함)
  ↓
Telegram 응답
```

---

## 배포 방법 (Railway, 15분)

### Step 1. GitHub repo 생성
```bash
cd C:\Users\njw85\
git clone 또는 새 폴더 생성
# 이 파일들 복사 후:
git init
git add .
git commit -m "init: JW telegram agent"
git remote add origin https://github.com/abillion-abillion/jw-telegram-agent
git push -u origin main
```

### Step 2. Railway 계정 및 프로젝트 생성
1. railway.app 접속 → GitHub 로그인
2. "New Project" → "Deploy from GitHub repo"
3. `jw-telegram-agent` 선택

### Step 3. 환경변수 등록
Railway 대시보드 → Variables 탭에서 아래 4개 등록:

| 변수명 | 값 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather에서 발급받은 토큰 |
| `ALLOWED_CHAT_ID` | 진우님 Telegram chat_id |
| `ANTHROPIC_API_KEY` | Claude API 키 |
| `WEBHOOK_URL` | (Step 4 이후 입력) |

### Step 4. 배포 URL 확인 후 WEBHOOK_URL 등록
1. Railway 배포 완료 후 도메인 확인 (예: `https://jw-agent-xxxx.up.railway.app`)
2. Variables에 `WEBHOOK_URL` = 위 URL 등록
3. 자동 재배포 대기 (1-2분)

### Step 5. Chat ID 확인 방법
Telegram에서 `@userinfobot` 검색 → 메시지 보내면 chat_id 알려줌

---

## 사용법

Telegram에서 JW 봇에게 자유롭게 메시지 보내면 됩니다.

### 예시 명령
```
카드뉴스 초안 짜줘 - 오늘 미국 금리 동결 소식 관련해서 30대 직장인 타겟으로

30대 맞벌이 고객한테 보낼 IRP 세액공제 안내 카카오 메시지 초안

이번주 핀사이트랩스 매크로 리포트 주제 3개 추천해줘

신규 고객 온보딩 체크리스트 보여줘
```

### 특수 명령어
- `/start` - 시작 안내
- `/clear` - 대화 기록 초기화 (새 주제 시작 시)
- `/help` - 도움말

---

## 월 비용 (Railway)
- Hobby 플랜: $5/월 (약 7,000원)
- 무료 크레딧 $5 제공 → 첫 달 무료

---

## 파일 구조
```
jw-telegram-agent/
├── main.py           ← 메인 서버
├── requirements.txt  ← 패키지 목록
├── Procfile          ← Railway 실행 명령
├── .env.example      ← 환경변수 예시
├── .gitignore        ← .env 제외
└── README.md         ← 이 파일
```

---

_관리자: 남진우 | 2026-04-09_
