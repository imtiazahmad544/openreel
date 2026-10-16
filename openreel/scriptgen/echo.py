"""Echo provider — deterministic offline fallback (also handy for tests).

Builds a simple structured script from the topic so the pipeline works
with zero network access.
"""
from __future__ import annotations

from .base import LLMProvider, WORDS_PER_MINUTE


class EchoProvider(LLMProvider):
    name = "echo"

    def complete(self, prompt: str) -> str:
        # Extract a topic-ish line for a readable fallback script.
        topic = prompt.split("about:")[-1].split("\n")[0].strip() or "this topic"
        paras = [
            f"Have you ever wondered about {topic}? In the next few minutes, "
            f"we are going to break it down step by step, with clear examples you can follow.",
            f"Let's start with the basics of {topic}. Understanding the fundamentals "
            f"gives you a solid foundation before we go deeper into the details.",
            f"Now for the interesting part. Here is what most people get wrong about {topic}, "
            f"and the simple ideas that actually work in practice.",
            f"To wrap up: {topic} rewards curiosity and consistent action. "
            f"If this helped, like and subscribe for the next one.",
        ]
        # Roughly scale paragraph count from the requested word target in prompt.
        return "\n\n".join(paras)
