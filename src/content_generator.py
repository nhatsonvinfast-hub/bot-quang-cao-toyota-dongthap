"""Generates Facebook post copy using Claude."""
from typing import Optional

import anthropic

import config

SYSTEM_PROMPT = """Bạn là chuyên viên content marketing cho Fanpage Facebook của
đại lý ô tô "{page_name}". Nhiệm vụ: viết bài đăng Facebook bằng tiếng Việt,
giọng văn chuyên nghiệp nhưng gần gũi, thu hút tương tác.

Yêu cầu định dạng:
- Mở đầu gây chú ý (hook) trong 1-2 câu đầu.
- Nội dung ngắn gọn, chia đoạn dễ đọc, có thể dùng emoji phù hợp (không lạm dụng).
- Kết thúc bằng lời kêu gọi hành động (CTA) rõ ràng.
- Thêm 3-5 hashtag liên quan ở cuối bài.
- Chỉ trả về nội dung bài đăng, không giải thích, không markdown, không tiêu đề.
"""


class ContentGenerator:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key or config.ANTHROPIC_API_KEY)
        self.model = model or config.CLAUDE_MODEL

    def generate_post(
        self,
        topic: str,
        tone: str = "chuyên nghiệp, gần gũi",
        cta: Optional[str] = None,
        max_words: int = 150,
    ) -> str:
        user_prompt = f"Chủ đề bài đăng: {topic}\nGiọng văn: {tone}\n"
        user_prompt += f"Độ dài tối đa: khoảng {max_words} từ.\n"
        if cta:
            user_prompt += f"CTA bắt buộc phải có: {cta}\n"

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT.format(page_name=config.FB_PAGE_NAME or "đại lý"),
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text.strip()

    def generate_variations(self, topic: str, n: int = 3, **kwargs) -> list[str]:
        return [self.generate_post(topic, **kwargs) for _ in range(n)]
