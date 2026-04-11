"""
card_news_handler.py
====================
기존 main.py에 추가하는 카드뉴스 파이프라인 모듈

적용 방법:
  1. 이 파일을 main.py 와 같은 폴더에 저장
  2. main.py 상단에 추가:
       from card_news_handler import handle_card_news_request, is_card_news_request
  3. main.py의 메시지 핸들러에 라우팅 추가 (아래 주석 참고)
"""

import asyncio
import logging
import tempfile
from pathlib import Path

import anthropic
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# ── 스킬 파일 로드 ────────────────────────────────────────────────────────────
def load_skill(skill_name: str) -> str:
    """skills/ 폴더에서 스킬 md 파일 로드"""
    skill_path = Path(__file__).parent / "skills" / f"{skill_name}.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return ""

CARD_NEWS_SKILL = load_skill("card_news")


# ── 트리거 감지 ───────────────────────────────────────────────────────────────
CARD_NEWS_TRIGGERS = [
    "카드뉴스", "인스타", "카드 만들어", "이미지 만들어",
    "sns 이미지", "3장", "슬라이드", "카드뉴스 만들어", "카드뉴스 만들어줘"
]

def is_card_news_request(text: str) -> bool:
    """카드뉴스 요청인지 감지"""
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in CARD_NEWS_TRIGGERS)


# ── 대장 → 부장 파이프라인 ────────────────────────────────────────────────────
DAEJANG_CARD_SYSTEM = """
당신은 JW대장입니다. 카드뉴스 요청을 받으면 skills/card_news.md 스킬을 활용해
JW부장에게 구체적인 HTML 생성 지시를 내립니다.

스킬 내용:
{skill}

지시 형식:
1. 요청 분석 (주제, 채널, 톤 파악)
2. 부장에게 카드뉴스 기획 지시 (1장/2장/3장 구성 명시)
3. 디자인 원칙 전달
4. HTML 출력 형식 명시 (---CARD_SPLIT--- 구분자 필수)

출력: 부장에게 보내는 지시문만 작성 (설명 없이)
""".format(skill=CARD_NEWS_SKILL)

BUJANG_CARD_SYSTEM = """
당신은 JW부장입니다. 대장의 지시에 따라 카드뉴스 HTML을 생성합니다.

규칙:
- HTML 3장을 ---CARD_SPLIT--- 으로 구분해서 출력
- 각 HTML은 완전한 독립 파일 (<!DOCTYPE html> 포함)
- 크기: 1080×1080px
- 디자인: 다크 네이비(#07192e) + 골드(#c9a96e)
- 폰트: Google Fonts Noto Serif KR + Noto Sans KR
- 카드번호: 01/03, 02/03, 03/03
- CTA: jwfinancial.co.kr 포함
- HTML 코드만 출력 (다른 텍스트 일절 금지)
"""

DAEJANG_REVIEW_SYSTEM = """
당신은 JW대장입니다. 부장이 생성한 카드뉴스 HTML을 검토합니다.

검토 기준:
- 3장 모두 ---CARD_SPLIT--- 구분됐는가
- 각 카드에 XX/03 번호 있는가
- CTA에 jwfinancial.co.kr 포함됐는가
- 1080×1080px 설정됐는가
- 다크 네이비 + 골드 디자인인가
- HTML 외 불필요 텍스트 없는가

이상 없으면: "✅ 대장 검토 완료" 한 줄만 출력
이상 있으면: 구체적 수정 지시 후 수정된 HTML 전체 재출력 (---CARD_SPLIT--- 포함)
"""


def call_claude(system: str, user_message: str, api_key: str, max_tokens: int = 8000) -> str:
    """Claude API 동기 호출"""
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text


async def run_pipeline(topic: str, api_key: str, progress_callback=None) -> list[str]:
    """
    대장 → 부장 → 대장 검토 파이프라인
    Returns: HTML 카드 3장 리스트
    """
    loop = asyncio.get_event_loop()

    # 1단계: 대장이 부장에게 지시
    if progress_callback:
        await progress_callback("✏️ JW대장이 카드뉴스 기획 중...")

    daejang_instruction = await loop.run_in_executor(
        None,
        call_claude,
        DAEJANG_CARD_SYSTEM,
        f"카드뉴스 요청: {topic}",
        api_key,
        1000,
    )
    logger.info(f"대장 지시:\n{daejang_instruction[:200]}...")

    # 2단계: 부장이 HTML 생성
    if progress_callback:
        await progress_callback("🎨 JW부장이 HTML 카드뉴스 작성 중...")

    bujang_output = await loop.run_in_executor(
        None,
        call_claude,
        BUJANG_CARD_SYSTEM,
        f"대장 지시:\n{daejang_instruction}\n\n주제: {topic}",
        api_key,
        8000,
    )

    # 3단계: 대장 검토
    if progress_callback:
        await progress_callback("🔍 JW대장이 검토 중...")

    review_result = await loop.run_in_executor(
        None,
        call_claude,
        DAEJANG_REVIEW_SYSTEM,
        f"부장 결과물:\n{bujang_output}",
        api_key,
        8000,
    )

    # 검토 통과 시 부장 결과물 사용, 수정 시 대장 재출력본 사용
    if "✅ 대장 검토 완료" in review_result:
        final_html_raw = bujang_output
        logger.info("대장 검토 통과")
    else:
        logger.info("대장이 수정 지시 → 수정본 사용")
        final_html_raw = review_result

    # HTML 파싱
    cards = [c.strip() for c in final_html_raw.split("---CARD_SPLIT---")]
    cards = [c for c in cards if "<!doctype" in c.lower() or "<html" in c.lower()]

    return cards[:3]


# ── HTML → PNG 변환 ───────────────────────────────────────────────────────────
async def html_to_png(html_content: str, output_path: Path, size: int = 1080):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": size, "height": size},
            device_scale_factor=2,
        )
        await page.set_content(html_content, wait_until="networkidle")
        await page.evaluate("document.fonts.ready")
        await page.wait_for_timeout(800)
        await page.screenshot(
            path=str(output_path),
            clip={"x": 0, "y": 0, "width": size, "height": size},
            type="png",
        )
        await browser.close()


# ── 텔레그램 핸들러 (main.py에서 호출) ───────────────────────────────────────
async def handle_card_news_request(update, context, api_key: str):
    """
    main.py 메시지 핸들러에서 호출:

    사용 예시 (main.py):
    ─────────────────────────────────────────────
    from card_news_handler import handle_card_news_request, is_card_news_request

    async def handle_message(update, context):
        text = update.message.text

        # 기존 라우팅 앞에 카드뉴스 감지 추가
        if is_card_news_request(text):
            await handle_card_news_request(update, context, ANTHROPIC_API_KEY)
            return

        # 기존 대장/부장 파이프라인 계속
        ...
    ─────────────────────────────────────────────
    """
    from telegram import InputMediaPhoto

    topic = update.message.text
    msg = await update.message.reply_text("📋 카드뉴스 파이프라인 시작...")

    async def progress(text: str):
        await msg.edit_text(text)

    try:
        # 파이프라인 실행
        cards_html = await run_pipeline(topic, api_key, progress_callback=progress)

        if not cards_html:
            await msg.edit_text("❌ HTML 생성 실패. 다시 시도해주세요.")
            return

        # PNG 변환
        await msg.edit_text(f"🖼 PNG 변환 중... ({len(cards_html)}장)")

        with tempfile.TemporaryDirectory() as tmpdir:
            png_paths = []
            for i, html in enumerate(cards_html, 1):
                png_path = Path(tmpdir) / f"card{i}.png"
                await html_to_png(html, png_path)
                png_paths.append(png_path)

            # 텔레그램 전송
            await msg.edit_text("📤 전송 중...")
            media_group = []
            for i, png_path in enumerate(png_paths):
                with open(png_path, "rb") as f:
                    media_group.append(
                        InputMediaPhoto(
                            media=f.read(),
                            caption=f"✅ 카드뉴스 {i+1}/3 — {topic[:30]}" if i == 0 else "",
                        )
                    )

            await update.message.reply_media_group(media=media_group)
            await msg.delete()

    except Exception as e:
        logger.error(f"카드뉴스 오류: {e}")
        await msg.edit_text(f"❌ 오류:\n{str(e)[:200]}")
