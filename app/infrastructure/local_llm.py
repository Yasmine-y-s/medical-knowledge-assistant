from app.domain.interfaces import LLM, LLMResponse


class LocalLLM(LLM):
    def generate(self, messages, tools=None, tool_choice=None):
        return LLMResponse(
            content="This is a placeholder response from LocalLLM — no real model was called.",
            tool_calls=None,
            prompt_tokens=0,
            completion_tokens=0,
        )