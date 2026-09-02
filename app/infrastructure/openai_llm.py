import os
from openai import OpenAI
from app.domain.interfaces import LLM, LLMResponse


class OpenAILLM(LLM):
    def __init__(self):
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def generate(self, messages, tools=None, tool_choice=None):
        kwargs = {"model": "gpt-5-nano", "messages": messages}

        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice

        completion = self.client.chat.completions.create(**kwargs)
        message = completion.choices[0].message
        usage = completion.usage

        return LLMResponse(
            content=message.content,
            tool_calls=message.tool_calls,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )