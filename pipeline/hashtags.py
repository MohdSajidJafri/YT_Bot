"""Channel-specific viral hashtag pools for YouTube Shorts descriptions.

Each channel preset gets a curated list of relevant, high-traffic hashtags.
The pipeline appends a rotating subset to the youtube_description before upload.
"""
from __future__ import annotations

import random

# ── Channel-specific hashtag pools ──────────────────────────────────────
# Each entry: list of hashtag groups (each group is a list of related tags).
# The pipeline picks 1-2 tags from each of the first 3-4 groups per upload.

HASHTAG_POOLS: dict[str, list[list[str]]] = {
    "ghost_stories": [
        ["#ghoststories", "#horrorstory", "#scarystories", "#paranormal"],
        ["#creepy", "#haunted", "#spooky", "#scary"],
        ["#storytime", "#reallifestory", "#truestory"],
        ["#horror", "#ghost", "#paranormalactivity"],
        ["#fyp", "#viral", "#shorts", "#youtubeshorts"],
    ],
    "facts": [
        ["#facts", "#interestingfacts", "#mindblowingfacts", "#didyouknow"],
        ["#factshorts", "#amazingfacts", "#randomfacts", "#dailyfacts"],
        ["#knowledge", "#education", "#learnontiktok", "#trivia"],
        ["#sciencefacts", "#historyfacts", "#psychologyfacts"],
        ["#fyp", "#viral", "#shorts", "#youtubeshorts"],
    ],
    "hindi_myth": [
        ["#हिंदूमिथोलॉजी", "#धार्मिककहानी", "#पौराणिककथा", "#भक्ति"],
        ["#शिवकथा", "#रामायण", "#महाभारत", "#गणेशकथा"],
        ["#hindumythology", "#hindugod", "#sanatandharma", "#bhakti"],
        ["#धार्मिक", "#पौराणिक", "#कथा", "#भगवान"],
        ["#fyp", "#viral", "#shorts", "#youtubeshorts"],
    ],
    "school_story": [
        ["#schoolstory", "#storytime", "#schoollife", "#dramastory"],
        ["#relatable", "#highschool", "#nostalgia", "#childhoodmemories"],
        ["#fictionalstory", "#storytelling", "#plot twist"],
        ["#fyp", "#viral", "#shorts", "#youtubeshorts"],
    ],
    "psych_tradeoff": [
        ["#psychology", "#psychologyfacts", "#humanbehavior", "#mindset"],
        ["#mentalhealth", "#selfimprovement", "#habits", "#motivation"],
        ["#psychologytips", "#behavioralscience", "#brainhacks"],
        ["#fyp", "#viral", "#shorts", "#youtubeshorts"],
    ],
    "history_micro": [
        ["#history", "#historyfacts", "#historical", "#onthisday"],
        ["#ancienthistory", "#worldhistory", "#didyouknow", "#historyshorts"],
        ["#forgottenhistory", "#historylover", "#past"],
        ["#fyp", "#viral", "#shorts", "#youtubeshorts"],
    ],
}

DEFAULT_HASHTAGS = ["#shorts", "#youtubeshorts", "#fyp", "#viral"]


def get_hashtag_string(channel_id: str, max_tags: int = 8) -> str:
    """Return a space-separated string of relevant hashtags for the channel.

    Picks 1-2 tags from each of the first 3-4 groups, then fills remaining
    from the generic pool, up to `max_tags`.
    """
    pool = HASHTAG_POOLS.get(channel_id, [])
    selected: list[str] = []

    # Pick from channel-specific groups
    for group in pool[:4]:
        if len(selected) >= max_tags:
            break
        # Pick 1-2 from each group
        n = min(random.randint(1, 2), len(group), max_tags - len(selected))
        selected.extend(random.sample(group, n))

    # Fill remaining with defaults
    remaining = max_tags - len(selected)
    if remaining > 0:
        defaults = [t for t in DEFAULT_HASHTAGS if t not in selected]
        selected.extend(random.sample(defaults, min(remaining, len(defaults))))

    return " ".join(selected)


def append_hashtags(description: str, channel_id: str, max_tags: int = 8) -> str:
    """Append a line of hashtags to the description if not already present."""
    tag_str = get_hashtag_string(channel_id, max_tags=max_tags)
    # Avoid duplicate hashtag blocks
    if tag_str in description:
        return description
    # Ensure there's a blank line before hashtags
    desc = description.rstrip()
    if desc and not desc.endswith("\n\n"):
        desc += "\n\n"
    return f"{desc}{tag_str}"