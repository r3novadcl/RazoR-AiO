import asyncio
import base64
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.emoji_sync import sync_application_emojis


def _decode_client_id(token: str) -> str | None:
    try:
        segment = token.split(".")[0]
        padded = segment + "=" * (-len(segment) % 4)
        decoded = base64.b64decode(padded).decode("utf-8")
        return decoded if decoded.isdigit() else None
    except Exception:
        return None


async def main():
    if not config.TOKEN:
        print("TOKEN is not set in .env — cannot sync emojis.")
        return

    client_id = config.CLIENT_ID or _decode_client_id(config.TOKEN)
    if not client_id:
        print("Could not resolve CLIENT_ID — set it explicitly in .env.")
        return

    uploaded = await sync_application_emojis(client_id, config.TOKEN)
    print(f"Done — {len(uploaded)} emoji(s) tracked in {config.UPLOADED_EMOJIS_JSON_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
