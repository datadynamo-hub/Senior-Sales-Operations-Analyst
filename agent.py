import streamlit as st
from openai import OpenAI

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
MODEL = "anthropic/claude-haiku-4-5"


def _client() -> OpenAI:
    return OpenAI(
        api_key=st.secrets["OPENROUTER_API_KEY"],
        base_url=OPENROUTER_BASE,
    )


class Agent:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    def answer(self, history: list[dict]) -> str:
        messages = [{"role": "system", "content": self.system_prompt}] + history
        try:
            response = _client().chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=400,
                temperature=0,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error contacting the assistant: {e}"
