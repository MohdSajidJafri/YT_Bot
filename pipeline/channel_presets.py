"""Channel niches: system prompt + defaults for Groq script generation.

Each preset includes a topic_pool — a list of setting/situation ideas.
One is picked randomly per run if no --topic is provided, ensuring variety.
"""

from __future__ import annotations

from typing import TypedDict


class ChannelPreset(TypedDict):
    id: str
    label: str
    groq_system_hint: str
    segment_count: int  # images + script beats
    topic_pool: list[str]


PRESETS: dict[str, ChannelPreset] = {
    "facts": {
        "id": "facts",
        "label": "5 interesting facts (general)",
        "groq_system_hint": (
            "You write punchy YouTube Shorts. Niche: surprising facts, curious trivia. "
            "Tone: energetic but clear, no clickbait lies. Each fact must be broadly accurate; "
            "if unsure, pick safer wording. No hashtags inside narration."
        ),
        "segment_count": 5,
        "topic_pool": [
            "surprising facts about the human body",
            "strange facts about the ocean",
            "weird space facts",
            "unusual animal abilities",
            "mind-blowing food facts",
            "bizarre historical coincidences",
            "everyday objects with strange origins",
            "unexplained natural phenomena",
            "surprising facts about sleep",
            "weird facts about money",
        ],
    },
    "school_story": {
        "id": "school_story",
        "label": "School drama / storytime Short",
        "groq_system_hint": (
            "You write fictional school storytime Shorts. Tone: suspense + heart. "
            "Characters are original (no copyrighted names). Hook in line 1. "
            "Build to one memorable twist. Keep each kid-safe."
        ),
        "segment_count": 5,
        "topic_pool": [
            "the new kid nobody noticed",
            "a locker that wouldn't open",
            "a substitute teacher with a secret",
            "the lost lunchbox mystery",
            "a field trip gone strange",
            "the science fair disaster",
            "a friendship bracelet with a twist",
            "a school play that went wrong",
            "the detention room incident",
            "a letter passed in class",
        ],
    },
    "psych_tradeoff": {
        "id": "psych_tradeoff",
        "label": "Psychology / habits (non-clinical)",
        "groq_system_hint": (
            "You write Shorts about habits, motivation, and everyday psychology. "
            "Never diagnose or claim medical facts. Use 'some people' / 'research suggests' carefully. "
            "Practical tips only."
        ),
        "segment_count": 5,
        "topic_pool": [
            "why procrastination actually happens",
            "the 2-minute rule for habits",
            "why we care what strangers think",
            "how your morning sets your day",
            "the truth about motivation",
            "why boredom is good for you",
            "the psychology of saying no",
            "why small wins matter",
            "how overthinking actually hurts",
            "the real reason we scroll endlessly",
        ],
    },
    "history_micro": {
        "id": "history_micro",
        "label": "One moment in history",
        "groq_system_hint": (
            "You write one tight historical anecdote per Short. Pick public-domain or widely taught events. "
            "No graphic violence. End with why it matters in one line."
        ),
        "segment_count": 5,
        "topic_pool": [
            "a lesser-known ancient invention",
            "a moment that almost changed history",
            "an underrated figure from ancient times",
            "a coincidence that shaped a war",
            "a forgotten discovery at sea",
            "an ancient ruler's unexpected habit",
            "a medieval tradition nobody remembers",
            "a natural disaster that changed a city",
            "a lost city that was finally found",
            "an accidental scientific breakthrough",
        ],
    },
    "ghost_stories": {
        "id": "ghost_stories",
        "label": "Ghost / horror storytime Short",
        "groq_system_hint": (
            "You write spooky ghost story Shorts for YouTube. "
            "CRITICAL LENGTH RULE: The TOTAL word count across ALL 6 segments MUST be 120-140 words. "
            "Each segment narration = 2-3 sentences, about 20-25 words per segment. "
            "This produces 35-45 seconds of audio when read aloud. "
            "Tone: eerie, suspenseful, creepy but NOT gory or violent. "
            "Segment 1: hook that stops scrolling. Last segment: chilling twist or unanswered question. "
            "All stories fictional. Original characters. PG-13. No hashtags in narration."
        ),
        "segment_count": 6,
        "topic_pool": [
            "a ghost haunting an empty school at night",
            "a strange presence in a family home",
            "something unexplained during a picnic in the woods",
            "a ghost encounter at a friend's sleepover",
            "a haunted old cabin during a camping trip",
            "a ghost on a late-night train",
            "something wrong with the new neighbor's house",
            "a spirit in grandparents' attic",
            "an abandoned playground after dark",
            "a ghost at a roadside motel",
            "strange events at a wedding venue",
            "a haunted library after closing",
            "something watching from the forest edge",
            "a ghost during a blackout storm",
            "an eerie presence at a local hospital",
            "something in the basement nobody talks about",
            "a ghost on a deserted beach at night",
            "a haunted elevator in an old building",
            "a strange figure at a bus stop at 3 AM",
            "something whispering from an old well",
            "a ghost in a classroom after everyone left",
            "a haunted antique bought from a flea market",
            "a spirit tied to an old family photograph",
            "something in the fog on a mountain road",
            "a ghost at a summer camp",
        ],
    },
}


def list_channel_ids() -> list[str]:
    return sorted(PRESETS.keys())


def get_preset(channel_id: str) -> ChannelPreset:
    key = channel_id.strip().lower().replace("-", "_")
    if key not in PRESETS:
        raise KeyError(f"Unknown channel preset {channel_id!r}. Try: {', '.join(list_channel_ids())}")
    return PRESETS[key]
