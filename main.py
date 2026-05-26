"""
오늘의 명언 텔레그램 봇
- 네이버 명언 검색 결과 크롤링
- 매일 랜덤 카테고리에서 2개 선택 (중복 방지)
- 텔레그램 발송 (TELEGRAM_CHAT_IDS에 등록된 대상)
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import random
import sys
from datetime import datetime, timezone, timedelta

# ── 설정 ──────────────────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).strftime("%Y-%m-%d")

CATEGORIES = {
    "공부":  "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blMy&qvt=0&query=%EA%B3%B5%EB%B6%80%20%EB%AA%85%EC%96%B8",
    "인생":  "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blMy&qvt=0&query=%EC%9D%B8%EC%83%9D%20%EB%AA%85%EC%96%B8",
    "성공":  "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blMy&qvt=0&query=%EC%84%B1%EA%B3%B5%20%EB%AA%85%EC%96%B8",
    "친구":  "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blMy&qvt=0&query=%EC%B9%9C%EA%B5%AC%20%EB%AA%85%EC%96%B8",
    "독서":  "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blMy&qvt=0&query=%EB%8F%85%EC%84%9C%20%EB%AA%85%EC%96%B8",
    "시간":  "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blMy&qvt=0&query=%EC%8B%9C%EA%B0%84%20%EB%AA%85%EC%96%B8",
    "노력":  "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blMy&qvt=0&query=%EB%85%B8%EB%A0%A5%20%EB%AA%85%EC%96%B8",
    "희망":  "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blMy&qvt=0&query=%ED%9D%AC%EB%A7%9D%20%EB%AA%85%EC%96%B8",
    "도전":  "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blMy&qvt=0&query=%EB%8F%84%EC%A0%84%20%EB%AA%85%EC%96%B8",
    "자신감": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blMy&qvt=0&query=%EC%9E%90%EC%8B%A0%EA%B0%90%20%EB%AA%85%EC%96%B8",
}

SENT_FILE = "sent_quotes.json"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_IDS  = [c.strip() for c in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()]

# 네이버 명언 위젯에서 사용되는 CSS 셀렉터 후보 목록
# (네이버 UI 업데이트에 대비해 여러 셀렉터를 순서대로 시도)
QUOTE_SELECTORS = [
    "li.line_quote",
    "div.quote_info",
    "li[class*='quote']",
    "div[class*='quote'] li",
    "ul.lst_quote li",
    "div.lst_type1 li",
    "div[id*='quote'] li",
    "span[class*='quote_txt']",
    "div[class*='word_phrs'] li",   # 네이버 명언 위젯 후보
    "li.type_quote",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": "https://www.naver.com/",
}

# ── 중복 기록 관리 ────────────────────────────────────────────────────
def load_sent() -> dict:
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_sent(data: dict):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def all_sent_quotes(sent: dict) -> set:
    """지금까지 발송된 모든 명언 텍스트를 집합으로 반환"""
    result = set()
    for day_data in sent.values():
        result.update(day_data.get("quotes", []))
    return result

# ── 크롤링 ────────────────────────────────────────────────────────────
def fetch_quotes(url: str, debug: bool = False) -> list[str]:
    """네이버 명언 검색 결과 페이지에서 명언 텍스트 목록 반환"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] 페이지 요청 실패: {e}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")

    if debug:
        # 디버그 모드: HTML 일부 출력으로 셀렉터 확인 도움
        print("\n  [DEBUG] 페이지 title:", soup.title.string if soup.title else "없음")
        sample = soup.get_text()[:500].replace("\n", " ")
        print(f"  [DEBUG] 본문 미리보기: {sample}\n")

    quotes = []
    for selector in QUOTE_SELECTORS:
        items = soup.select(selector)
        if items:
            texts = [item.get_text(separator=" ", strip=True) for item in items]
            # 너무 짧거나 긴 항목 제거 (명언이 아닌 UI 텍스트 필터링)
            texts = [t for t in texts if 10 <= len(t) <= 300]
            if texts:
                if debug:
                    print(f"  [DEBUG] 셀렉터 '{selector}' → {len(texts)}개 발견")
                    for t in texts[:3]:
                        print(f"    ▸ {t[:80]}")
                quotes = texts
                break

    if not quotes:
        print(f"  [WARN] 명언을 찾지 못했습니다. URL: {url}")
    return quotes

# ── 텔레그램 발송 ─────────────────────────────────────────────────────
def send_telegram(chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        res = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        res.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"  [ERROR] 텔레그램 발송 실패 (chat_id={chat_id}): {e}")
        return False

def format_message(category: str, quotes: list[str]) -> str:
    category_emoji = {
        "공부": "📖", "인생": "🌿", "성공": "🏆", "친구": "🤝",
        "독서": "📚", "시간": "⏰", "노력": "💪", "희망": "🌅",
        "도전": "🚀", "자신감": "✨",
    }
    emoji = category_emoji.get(category, "💬")
    lines = [f"{emoji} <b>오늘의 명언 [{category}]</b>\n"]
    for i, q in enumerate(quotes, 1):
        lines.append(f"{i}. {q}\n")
    lines.append(f"\n📅 {TODAY}")
    return "\n".join(lines)

# ── 메인 ─────────────────────────────────────────────────────────────
def main():
    debug = "--debug" in sys.argv
    print(f"[{TODAY}] 명언 봇 시작")

    # 환경변수 확인
    if not BOT_TOKEN:
        print("[ERROR] TELEGRAM_BOT_TOKEN 환경변수가 없습니다.")
        sys.exit(1)
    if not CHAT_IDS:
        print("[ERROR] TELEGRAM_CHAT_IDS 환경변수가 없습니다.")
        sys.exit(1)

    sent = load_sent()

    # 오늘 이미 발송했으면 중복 실행 방지
    if TODAY in sent:
        print(f"[SKIP] 오늘({TODAY})은 이미 발송 완료되었습니다.")
        return

    previously_sent = all_sent_quotes(sent)
    print(f"누적 발송 명언 수: {len(previously_sent)}개")

    # 카테고리 순서를 랜덤하게 섞어서 순차 시도
    categories = list(CATEGORIES.items())
    random.shuffle(categories)

    selected_quotes = []
    selected_category = None

    for cat_name, url in categories:
        print(f"\n카테고리 [{cat_name}] 시도 중...")
        all_quotes = fetch_quotes(url, debug=debug)
        available = [q for q in all_quotes if q not in previously_sent]
        print(f"  전체: {len(all_quotes)}개 / 미발송: {len(available)}개")

        if len(available) >= 2:
            selected_quotes = random.sample(available, 2)
            selected_category = cat_name
            print(f"  ✅ [{cat_name}] 선택 완료")
            break

    if len(selected_quotes) < 2:
        print("[ERROR] 발송 가능한 명언이 부족합니다. (크롤링 실패 또는 모두 발송 완료)")
        sys.exit(1)

    # 메시지 구성 및 발송
    message = format_message(selected_category, selected_quotes)
    print(f"\n발송 메시지:\n{message}\n")

    success_count = 0
    for chat_id in CHAT_IDS:
        if send_telegram(chat_id, message):
            print(f"  ✅ 발송 성공: {chat_id}")
            success_count += 1
        else:
            print(f"  ❌ 발송 실패: {chat_id}")

    if success_count == 0:
        print("[ERROR] 모든 발송이 실패했습니다.")
        sys.exit(1)

    # 발송 기록 저장
    sent[TODAY] = {
        "category": selected_category,
        "quotes": selected_quotes,
    }
    save_sent(sent)
    print(f"\n[완료] {selected_category} 명언 {len(selected_quotes)}개 → {success_count}명에게 발송 성공")

if __name__ == "__main__":
    main()
