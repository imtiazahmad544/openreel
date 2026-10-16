"""SEO pack: titles, description, tags, chapters, hashtags — via the free LLM."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .config import Settings
from .scriptgen.base import get_provider


@dataclass
class SEOPack:
    titles: list[str] = field(default_factory=list)      # 3 options, best first
    description: str = ""
    tags: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    chapters: list[tuple[str, str]] = field(default_factory=list)  # (timestamp, label)
    pinned_comment: str = ""

    @property
    def best_title(self) -> str:
        return self.titles[0] if self.titles else ""


def _chapters_from_scenes(scenes: list[dict]) -> list[tuple[str, str]]:
    out = []
    for s in scenes:
        start = int(s.get("start", 0))
        label = " ".join(s.get("text", "").split()[:6]).rstrip(".,") or f"Part {s.get('index', 0)+1}"
        out.append((f"{start // 60:02d}:{start % 60:02d}", label))
    return out


def generate_seo_pack(topic: str, script: str, scenes: list[dict],
                      settings: Settings) -> SEOPack:
    """Ask the (free) LLM for packaging; chapters come from real scene timings."""
    prompt = (
        "You are a YouTube SEO expert. For the video below, reply with ONLY valid JSON "
        "(no markdown, no commentary) with keys: titles (array of 3 click-worthy titles "
        "under 60 chars, best first), description (2 short paragraphs + call to action, "
        "no timestamps), tags (array of 12), hashtags (array of 3, with #), "
        "pinned_comment (one engaging question under 200 chars).\n\n"
        f"Topic: {topic}\nScript excerpt: {script[:1500]}"
    )
    provider = get_provider(settings)
    raw = provider.complete_retry(prompt)
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    data = json.loads(m.group(0)) if m else {}
    return SEOPack(
        titles=[t for t in data.get("titles", []) if isinstance(t, str)][:3],
        description=str(data.get("description", "")),
        tags=[t for t in data.get("tags", []) if isinstance(t, str)][:15],
        hashtags=[t for t in data.get("hashtags", []) if isinstance(t, str)][:5],
        chapters=_chapters_from_scenes(scenes),
        pinned_comment=str(data.get("pinned_comment", "")),
    )


def description_with_chapters(pack: SEOPack) -> str:
    """Full description incl. chapter timestamps for the YouTube description box."""
    parts = [pack.description.strip()]
    if pack.chapters:
        parts.append("\nChapters:")
        parts += [f"{ts} {label}" for ts, label in pack.chapters]
    if pack.hashtags:
        parts.append("\n" + " ".join(pack.hashtags))
    return "\n".join(p for p in parts if p)
