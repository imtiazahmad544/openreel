"""Topic research: trend-aware video ideas with scores, via the free LLM."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .config import Settings
from .scriptgen.base import get_provider


@dataclass
class TopicIdea:
    topic: str
    hook: str
    angle: str
    score: int  # 0-100: demand x feasibility for a faceless channel


def ideate_topics(niche: str, count: int, settings: Settings) -> list[TopicIdea]:
    prompt = (
        "You are a YouTube strategist for faceless automation channels. "
        f"Suggest {count} video topics in this niche: {niche}. "
        "Reply with ONLY valid JSON: an array of objects with keys "
        "topic, hook (first-15-seconds spoken hook), angle (what makes this video "
        "different), score (0-100 for demand x ease of production with stock/AI visuals). "
        "No markdown, no commentary."
    )
    provider = get_provider(settings)
    raw = provider.complete_retry(prompt)
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    ideas = []
    if m:
        for item in json.loads(m.group(0)):
            try:
                ideas.append(TopicIdea(
                    topic=str(item["topic"]), hook=str(item.get("hook", "")),
                    angle=str(item.get("angle", "")),
                    score=max(0, min(100, int(item.get("score", 50)))))
                )
            except (KeyError, ValueError, TypeError):
                continue
    return sorted(ideas, key=lambda i: i.score, reverse=True)
