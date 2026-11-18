#!/usr/bin/env python3
"""List all available models for your configured API key (.env or ChatAnywhere)."""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Load .env (supports both python-dotenv and pure Python parsing)
REPO_ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    env_file = REPO_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main():
    api_key = sys.argv[1].strip() if len(sys.argv) > 1 else os.environ.get("OPENAI_API_KEY", "").strip()
    base_url = sys.argv[2].strip() if len(sys.argv) > 2 else os.environ.get("OPENAI_BASE_URL", "https://api.chatanywhere.org/v1").strip()

    if not api_key or "your_" in api_key:
        print("❌ Error: No valid API key found.")
        print("   Please make sure OPENAI_API_KEY is set in YT_Bot/.env")
        print("   Or pass it: python scripts/check_openai_models.py sk-...")
        sys.exit(1)

    base_url = base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

    print(f"📡 Querying available models from {base_url} ...")

    req = urllib.request.Request(
        f"{base_url}/models",
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            all_models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
            all_models = sorted(list(set(all_models)))

            if not all_models:
                print("No models returned in the response list.")
                return

            print(f"\n🎉 Total models supported by this endpoint: {len(all_models)}\n" + "=" * 60)

            # Categorize
            gpt_models = [m for m in all_models if "gpt" in m.lower() or "o1" in m.lower() or "o3" in m.lower()]
            claude_models = [m for m in all_models if "claude" in m.lower()]
            deepseek_models = [m for m in all_models if "deepseek" in m.lower()]
            gemini_models = [m for m in all_models if "gemini" in m.lower()]
            other_models = [
                m for m in all_models
                if m not in gpt_models and m not in claude_models and m not in deepseek_models and m not in gemini_models
            ]

            if gpt_models:
                print("🧠 OpenAI Models:")
                for m in gpt_models:
                    # Highlight recommended/free tier model
                    tag = " ⭐ (Recommended & Free on ChatAnywhere)" if m in ("gpt-4o-mini", "gpt-3.5-turbo") else ""
                    print(f"   • {m}{tag}")

            if claude_models:
                print("\n🎭 Anthropic / Claude Models:")
                for m in claude_models:
                    print(f"   • {m}")

            if deepseek_models:
                print("\n🐋 DeepSeek Models:")
                for m in deepseek_models:
                    print(f"   • {m}")

            if gemini_models:
                print("\n✨ Google Gemini Models:")
                for m in gemini_models:
                    print(f"   • {m}")

            if other_models:
                print(f"\n🌐 Other Models ({len(other_models)}):")
                for m in other_models:
                    print(f"   • {m}")

            print("=" * 60)
            print("\n💡 Tip: To switch models, simply change OPENAI_MODEL in your YT_Bot/.env file!")

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"❌ Failed to fetch models (HTTP {e.code}): {err_body}")
    except Exception as e:
        print(f"❌ Connection error: {e}")


if __name__ == "__main__":
    main()
