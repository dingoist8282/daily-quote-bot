"""
오늘의 명언 텔레그램 봇
- quotes.json에서 랜덤 카테고리 명언 2개 선택 (중복 방지)
- 텔레그램 발송 (TELEGRAM_CHAT_IDS에 등록된 대상)
"""

import requests
import json
import os
import random
import sys
from datetime import datetime, timezone, timedelta

# ── 설정 ──────────────────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).strftime("%Y-%m-%d")

QUOTES_FILE = "quotes.json"
SENT_FILE   = "sent_quotes.json"
BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_IDS    = [c.strip() for c in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()]

CATEGORY_EMOJI = {
    "공부": "📖", "인생": "🌿", "성공": "🏆", "친구": "🤝",
    "독서": "📚", "시간": "⏰", "노력": "💪", "희망": "🌅",
    "도전": "🚀", "자신감": "✨",
}

# ── 파일 관리 ─────────────────────────────────────────────────────────
def load_quotes() -> list:
    with open(QUOTES_FILE, encoding="utf-8") as f:
        return json.load(f)

def load_sent() -> dict:
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_sent(data: dict):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def all_sent_texts(sent: dict) -> set:
    result = set()
    for day_data in sent.values():
        result.update(day_data.get("quotes", []))
    return result

# ── 명언 선택 ─────────────────────────────────────────────────────────
def pick_quotes(all_quotes: list, sent_texts: set) -> tuple[str, list]:
    """랜덤 카테고리에서 미발송 명언 2개 선택 → (카테고리, [명언텍스트, ...])"""
    categories = list({q["category"] for q in all_quotes})
    random.shuffle(categories)

    for category in categories:
        pool = [q for q in all_quotes if q["category"] == category]
        available = [q for q in pool if q["text"] not in sent_texts]
        if len(available) >= 3:
            chosen = random.sample(available, 3)
            return category, chosen

    return None, []

# ── 텔레그램 발송 ─────────────────────────────────────────────────────
def format_message(category: str, quotes: list) -> str:
    emoji = CATEGORY_EMOJI.get(category, "💬")
    lines = [f"{emoji} 오늘의 명언 [{category}]", ""]
    for i, q in enumerate(quotes, 1):
        lines.append(f"{i}. {q['text']}")
        lines.append(f"   — {q['author']}")
        lines.append("")
    lines.append(f"📅 {TODAY}")
    return "\n".join(lines)

def send_telegram(chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        res = requests.post(
            url,
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        res.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"  [ERROR] 발송 실패 (chat_id={chat_id}): {e}")
        try:
            print(f"  [ERROR] 텔레그램 응답: {e.response.json()}")
        except Exception:
            pass
        return False

# ── 메인 ─────────────────────────────────────────────────────────────
def main():
    print(f"[{TODAY}] 명언 봇 시작")

    if not BOT_TOKEN:
        print("[ERROR] TELEGRAM_BOT_TOKEN 환경변수가 없습니다.")
        sys.exit(1)
    if not CHAT_IDS:
        print("[ERROR] TELEGRAM_CHAT_IDS 환경변수가 없습니다.")
        sys.exit(1)

    sent = load_sent()

    if TODAY in sent:
        print(f"[SKIP] 오늘({TODAY})은 이미 발송 완료되었습니다.")
        return

    all_quotes  = load_quotes()
    sent_texts  = all_sent_texts(sent)
    print(f"전체 명언: {len(all_quotes)}개 / 누적 발송: {len(sent_texts)}개 / 남은 명언: {len(all_quotes) - len(sent_texts)}개")

    category, chosen = pick_quotes(all_quotes, sent_texts)

    if not chosen:
        print("[ERROR] 발송 가능한 명언이 없습니다. quotes.json을 보충해주세요.")
        sys.exit(1)

    message = format_message(category, chosen)
    print(f"\n발송 메시지:\n{message}\n")

    success = sum(1 for cid in CHAT_IDS if send_telegram(cid, message))

    if success == 0:
        print("[ERROR] 모든 발송이 실패했습니다.")
        sys.exit(1)

    sent[TODAY] = {
        "category": category,
        "quotes": [q["text"] for q in chosen],
    }
    save_sent(sent)
    print(f"[완료] [{category}] 명언 3개 → {success}명 발송 성공")

if __name__ == "__main__":
    main()
