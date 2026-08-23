#!/usr/bin/env python3
"""
Unit and integration tests for Groq script generation and fallback handling.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from groq import BadRequestError
from pipeline.channel_presets import get_preset
from pipeline.groq_script import (
    _clean_json_text,
    _parse_json_safely,
    _call_groq,
    generate_short_pack,
)


class TestGroqJsonParsing(unittest.TestCase):
    def test_direct_valid_json(self):
        raw = '{"youtube_title": "Spooky Night", "full_narration": "A chilling tale."}'
        data = _parse_json_safely(raw)
        self.assertEqual(data["youtube_title"], "Spooky Night")
        self.assertEqual(data["full_narration"], "A chilling tale.")

    def test_markdown_code_block(self):
        raw = """Here is the JSON you requested:
```json
{
  "youtube_title": "The Whispering Walls",
  "full_narration": "Every night at 3 AM the walls spoke."
}
```
Hope you like it!"""
        data = _parse_json_safely(raw)
        self.assertEqual(data["youtube_title"], "The Whispering Walls")

    def test_trailing_commas(self):
        raw = """{
  "youtube_title": "Mystery solved",
  "image_prompts": [
    "prompt 1",
    "prompt 2",
  ],
}"""
        data = _parse_json_safely(raw)
        self.assertEqual(len(data["image_prompts"]), 2)
        self.assertEqual(data["youtube_title"], "Mystery solved")

    def test_empty_or_invalid_raises(self):
        with self.assertRaises(ValueError):
            _parse_json_safely("")

        with self.assertRaises(ValueError):
            _parse_json_safely("just plain text with no json braces")


class TestGroqCallFallbacks(unittest.TestCase):
    def setUp(self):
        self.preset = get_preset("ghost_stories")

    def test_reasoning_and_json_validate_fallback(self):
        """Simulate Groq returning json_validate_failed on initial strategy and succeeding on fallback."""
        fake_json = {
            "youtube_title": "The Haunted Classroom 👻",
            "youtube_description": "A spooky mystery. #Shorts",
            "pinned_comment": "Would you stay after dark?",
            "full_narration": "The classroom clock ticks backwards at midnight when the lights flicker off completely. " * 5,
            "image_prompts": [f"Visual description {i+1}" for i in range(6)],
        }

        mock_choice_fail = MagicMock()
        mock_choice_success = MagicMock()
        mock_choice_success.message.content = "```json\n" + json.dumps(fake_json) + "\n```"

        mock_resp_success = MagicMock()
        mock_resp_success.choices = [mock_choice_success]

        call_count = 0

        def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First attempt fails with json_validate_failed 400
                response_mock = MagicMock()
                response_mock.status_code = 400
                response_mock.headers = {}
                raise BadRequestError(
                    message="Failed to validate JSON. Please adjust your prompt. See 'failed_generation' for more details.",
                    response=response_mock,
                    body={"error": {"code": "json_validate_failed", "failed_generation": ""}},
                )
            return mock_resp_success

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = fake_create

        with patch.dict("os.environ", {"GROQ_API_KEY": "dummy_key", "GROQ_MODEL": "openai/gpt-oss-20b"}):
            with patch("pipeline.groq_script.Groq", return_value=mock_client):
                result = _call_groq(self.preset, "Generate a ghost story")

        self.assertEqual(result["youtube_title"], "The Haunted Classroom 👻")
        self.assertGreaterEqual(call_count, 2)
        print("✓ Groq json_validate_failed fallback test passed")

    def test_generate_short_pack_end_to_end_single_variant(self):
        """Test full generate_short_pack execution for ghost_stories."""
        narration_words = [f"word{i}" for i in range(125)]
        fake_json = {
            "youtube_title": "The Echo in the Hallway 👻",
            "youtube_description": "Spooky story. #Shorts",
            "pinned_comment": "Did you hear that sound?",
            "full_narration": " ".join(narration_words),
            "image_prompts": [f"Image scene beat {i+1}" for i in range(6)],
        }

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(fake_json)
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp

        with patch.dict("os.environ", {"GROQ_API_KEY": "dummy_key"}):
            with patch("pipeline.groq_script.Groq", return_value=mock_client):
                pack = generate_short_pack(self.preset, topic_hint="an empty school")

        self.assertEqual(pack["youtube_title"], "The Echo in the Hallway 👻")
        self.assertEqual(len(pack["image_prompts"]), 6)
        self.assertEqual(len(pack["full_narration"].split()), 125)
        print("✓ generate_short_pack single-variant test passed")

    def test_generate_short_pack_end_to_end_multivariant(self):
        """Test full generate_short_pack execution for bilingual facts preset."""
        preset = get_preset("facts")
        en_words = [f"factword{i}" for i in range(130)]
        hi_words = [f"तथ्य{i}" for i in range(140)]

        fake_json = {
            "image_prompts": [f"Documentary photo {i+1}" for i in range(5)],
            "variants": {
                "en": {
                    "youtube_title": "Mind Blowing Space Facts 🚀",
                    "youtube_description": "Did you know this? #Shorts",
                    "pinned_comment": "Which fact surprised you the most?",
                    "full_narration": " ".join(en_words),
                },
                "hi": {
                    "youtube_title": "अविश्वसनीय अंतरिक्ष रहस्य 🚀",
                    "youtube_description": "क्या आप जानते थे? #Shorts",
                    "pinned_comment": "आपको कौन सा तथ्य सबसे ज्यादा पसंद आया?",
                    "full_narration": " ".join(hi_words),
                },
            },
        }

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(fake_json)
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp

        with patch.dict("os.environ", {"GROQ_API_KEY": "dummy_key"}):
            with patch("pipeline.groq_script.Groq", return_value=mock_client):
                pack = generate_short_pack(preset, topic_hint="black holes")

        self.assertIn("variants", pack)
        self.assertIn("en", pack["variants"])
        self.assertIn("hi", pack["variants"])
        self.assertEqual(len(pack["image_prompts"]), 5)
        print("✓ generate_short_pack bilingual multivariant test passed")


if __name__ == "__main__":
    unittest.main()
