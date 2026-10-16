import pytest

from openreel.config import Settings
from openreel.scriptgen.splitter import (
    Scene, split_script, words_for_duration, WORDS_PER_SCENE,
)
from openreel.scriptgen.base import build_script_prompt, get_provider, WORDS_PER_MINUTE
from openreel.scriptgen.echo import EchoProvider


def test_words_for_duration():
    assert words_for_duration(1.0) == WORDS_PER_MINUTE
    assert words_for_duration(0.5) == WORDS_PER_MINUTE // 2
    with pytest.raises(ValueError):
        words_for_duration(0)


def test_split_script_paragraphs_become_scenes():
    p1 = ("First paragraph about oceans and the mysterious creatures living in the deep "
          "dark water far below the sunny surface waves where light barely reaches.")
    p2 = ("Second paragraph about deserts and the resilient animals that survive the burning "
          "heat with almost no water at all through remarkable adaptations evolved over millennia.")
    scenes = split_script(p1 + "\n\n" + p2)
    assert len(scenes) == 2
    assert all(isinstance(s, Scene) for s in scenes)
    assert scenes[0].visual_prompt  # each scene gets an image prompt
    assert scenes[0].keywords  # and stock-search keywords


def test_split_script_long_paragraph_is_chunked():
    para = " ".join(f"word{i}." for i in range(300))
    scenes = split_script(para, max_scene_words=WORDS_PER_SCENE)
    assert len(scenes) > 1
    assert all(s.word_count <= WORDS_PER_SCENE + 20 for s in scenes)


def test_split_script_tiny_tail_merges():
    script = " ".join(f"word{i}." for i in range(70)) + "\n\ntiny tail."
    scenes = split_script(script, max_scene_words=WORDS_PER_SCENE)
    assert len(scenes) == 1  # tail merged instead of becoming its own scene
    assert "tiny tail." in scenes[0].text


def test_scene_est_seconds():
    s = Scene(index=0, text=" ".join(["w"] * WORDS_PER_MINUTE))
    assert s.est_seconds == pytest.approx(60.0)


def test_build_script_prompt_targets_duration():
    p = build_script_prompt("black holes", 450)
    assert "black holes" in p and "450" in p


def test_get_provider_defaults_to_pollinations():
    from openreel.scriptgen.pollinations import PollinationsProvider
    assert isinstance(get_provider(Settings()), PollinationsProvider)


def test_get_provider_echo_and_unknown_fallback():
    s = Settings()
    s.llm = "echo"
    assert isinstance(get_provider(s), EchoProvider)
    s.llm = "nope-not-real"
    from openreel.scriptgen.pollinations import PollinationsProvider
    assert isinstance(get_provider(s), PollinationsProvider)


def test_echo_provider_offline():
    s = Settings()
    out = EchoProvider(s).complete("Write about: the moon\nblah")
    assert "moon" in out
