# llm/client.py
import json
from openai import OpenAI
from ..config import config


class LLMClient:
    """大模型客户端"""

    def __init__(self):
        llm_config = config["llm"]
        self.provider = llm_config.get("provider", "openai")
        self.model = llm_config.get("model", "gpt-4o-mini")
        self.temperature = llm_config.get("temperature", 0.3)

        if self.provider == "openai":
            self.client = OpenAI(
                api_key=llm_config.get("api_key", ""),
                base_url=llm_config.get("base_url") or None,
            )
        elif self.provider == "anthropic":
            import anthropic

            self.client = anthropic.Anthropic(api_key=llm_config.get("api_key", ""))
        else:
            raise ValueError(f"不支持的LLM provider: {self.provider}")

    def extract_time_blocks(self, text: str, prompt_template: str) -> list:
        """调用大模型提取时间块"""
        from .prompt import TIME_EXTRACTION_PROMPT

        if self.provider == "openai":
            return self._extract_openai(text, TIME_EXTRACTION_PROMPT)
        elif self.provider == "anthropic":
            return self._extract_anthropic(text, TIME_EXTRACTION_PROMPT)

    def _extract_openai(self, text: str, prompt: str) -> list:
        """使用OpenAI API提取"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"请分析以下日记内容，提取时间数据：\n\n{text}",
                },
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return json.loads(content).get("time_blocks", [])

    def _extract_anthropic(self, text: str, prompt: str) -> list:
        """使用Anthropic API提取"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"请分析以下日记内容，提取时间数据：\n\n{text}",
                }
            ],
        )

        content = response.content[0].text
        return json.loads(content).get("time_blocks", [])


def get_llm_client():
    """获取LLM客户端单例"""
    if not hasattr(get_llm_client, "_instance"):
        get_llm_client._instance = LLMClient()
    return get_llm_client._instance
