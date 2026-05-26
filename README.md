# 📚 오늘의 명언 텔레그램 봇

네이버 명언 검색에서 매일 랜덤 카테고리의 명언 2개를 텔레그램으로 발송합니다.

## 발송 카테고리
공부 / 인생 / 성공 / 친구 / 독서 / 시간 / 노력 / 희망 / 도전 / 자신감

---

## 세팅 방법

### 1. GitHub Secrets 등록
레포지토리 → **Settings → Secrets and variables → Actions → New repository secret**

| Secret 이름 | 값 예시 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | `123456789:ABCdef...` |
| `TELEGRAM_CHAT_IDS` | `111111111,222222222` (콤마로 구분) |

> chat_id 확인 방법: 봇에게 메시지 전송 후  
> `https://api.telegram.org/bot<TOKEN>/getUpdates` 접속

### 2. Actions 권한 설정
레포지토리 → **Settings → Actions → General**  
→ Workflow permissions: **Read and write permissions** 선택

### 3. 자동 실행
- 매일 **오전 7시 KST** 자동 실행 (UTC 22:00)
- 수동 실행: Actions 탭 → "오늘의 명언 발송" → **Run workflow**

---

## 로컬 테스트

```bash
pip install -r requirements.txt

# 환경변수 설정 후 실행
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_IDS="your_chat_id"

python main.py

# 크롤링 디버그 모드 (셀렉터 확인)
python main.py --debug
```

---

## 파일 구조

```
quote-bot/
├── main.py              # 메인 로직
├── sent_quotes.json     # 발송 기록 (자동 업데이트)
├── requirements.txt
└── .github/workflows/
    └── daily.yml        # 스케줄 실행 설정
```

## sent_quotes.json 구조

```json
{
  "2026-05-26": {
    "category": "노력",
    "quotes": ["명언1", "명언2"]
  }
}
```

---

## 문제 해결

### 크롤링 실패 시
`python main.py --debug` 실행 후 출력된 페이지 미리보기로  
`main.py` 내 `QUOTE_SELECTORS` 목록에 해당 CSS 셀렉터를 추가하세요.

### Actions 실행 안 될 때
GitHub는 60일간 커밋이 없으면 스케줄 Actions를 비활성화합니다.  
`sent_quotes.json`이 매일 자동 커밋되므로 정상 작동 중엔 문제없습니다.
