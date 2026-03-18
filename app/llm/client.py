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
        self.temperature = llm_config.get("temperature", 0.0)
        self.timeout = llm_config.get("timeout", 60)

        if self.provider == "openai":
            self.client = OpenAI(
                api_key=llm_config.get("api_key", ""),
                base_url=llm_config.get("base_url") or None,
                timeout=self.timeout,
            )
        elif self.provider == "anthropic":
            import anthropic

            self.client = anthropic.Anthropic(
                api_key=llm_config.get("api_key", ""),
                timeout=self.timeout,
            )
        else:
            raise ValueError(f"不支持的LLM provider: {self.provider}")

    def extract_time_points(
        self,
        text: str,
        date: str,
        categories: str = "",
    ) -> list:
        """第1次调用：提取时间点序列"""
        from .prompt import TIME_POINT_EXTRACTION_PROMPT

        prompt = TIME_POINT_EXTRACTION_PROMPT.replace("{date}", date)
        prompt = prompt.replace("{categories}", categories or "无")

        if self.provider == "openai":
            return self._extract_openai_time_points(text, prompt)
        elif self.provider == "anthropic":
            return self._extract_anthropic_time_points(text, prompt)

    def classify_events(
        self,
        events: list,
        categories: str = "",
    ) -> list:
        """第2次调用：为事件分类"""
        from .prompt import CATEGORY_CLASSIFY_PROMPT

        prompt = CATEGORY_CLASSIFY_PROMPT.replace("{categories}", categories or "无")

        events_text = json.dumps({"events": events}, ensure_ascii=False)

        if self.provider == "openai":
            return self._extract_openai_classify(events_text, prompt)
        elif self.provider == "anthropic":
            return self._extract_anthropic_classify(events_text, prompt)

    def extract_event_details(
        self,
        diary_content: str,
        time_points: list,
    ) -> list:
        """第2次调用：逐个询问每个事件具体在做什么"""
        from .prompt import EVENT_DETAIL_PROMPT

        # 构建时间点序列文本
        time_points_text = "\n".join(
            [f"- {tp.get('time')}: {tp.get('event')}" for tp in time_points]
        )

        prompt = EVENT_DETAIL_PROMPT.replace("{diary_content}", diary_content)
        prompt = prompt.replace("{time_points}", time_points_text)

        if self.provider == "openai":
            return self._extract_openai_event_details(prompt)
        elif self.provider == "anthropic":
            return self._extract_anthropic_event_details(prompt)

    def _extract_openai_time_points(self, text: str, prompt: str) -> list:
        """使用OpenAI API提取时间点"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"请分析以下日记，提取时间点序列：\n\n{text}",
                },
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return json.loads(content).get("time_points", [])

    def _extract_anthropic_time_points(self, text: str, prompt: str) -> list:
        """使用Anthropic API提取时间点"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"请分析以下日记，提取时间点序列：\n\n{text}",
                }
            ],
        )

        content = response.content[0].text
        return json.loads(content).get("time_points", [])

    def _extract_openai_classify(self, events_text: str, prompt: str) -> list:
        """使用OpenAI API分类事件"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"请为以下事件分类：\n\n{events_text}",
                },
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return json.loads(content).get("classified", [])

    def _extract_anthropic_classify(self, events_text: str, prompt: str) -> list:
        """使用Anthropic API分类事件"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"请为以下事件分类：\n\n{events_text}",
                }
            ],
        )

        content = response.content[0].text
        return json.loads(content).get("classified", [])

    def _extract_openai_event_details(self, prompt: str) -> list:
        """使用OpenAI API提取事件详情"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return json.loads(content).get("details", [])

    def _extract_anthropic_event_details(self, prompt: str) -> list:
        """使用Anthropic API提取事件详情"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=prompt,
            messages=[{"role": "user", "content": "请分析以上内容"}],
        )

        content = response.content[0].text
        return json.loads(content).get("details", [])


def get_llm_client():
    """获取LLM客户端单例"""
    if not hasattr(get_llm_client, "_instance"):
        get_llm_client._instance = LLMClient()
    return get_llm_client._instance
