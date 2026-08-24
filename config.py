import os
from dotenv import load_dotenv

load_dotenv()


def _split_ids(raw: str) -> list[int]:
    return [int(x) for x in raw.split(",") if x.strip().isdigit()]


def _hex_color(raw: str, fallback: int) -> int:
    if not raw:
        return fallback
    try:
        return int(raw.replace("#", ""), 16)
    except ValueError:
        return fallback


TOKEN = os.getenv("TOKEN", "")
CLIENT_ID = os.getenv("CLIENT_ID", "")

BOT_NAME = os.getenv("BOT_NAME", "RazoR")
PREFIX = os.getenv("PREFIX", "!")
OWNER_IDS = _split_ids(os.getenv("OWNER_IDS", ""))

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/razor.sqlite3")

EMBED_COLOR = _hex_color(os.getenv("EMBED_COLOR", ""), 0x2B2D31)
EMBED_COLOR_OK = _hex_color(os.getenv("EMBED_COLOR_OK", ""), 0x57F287)
EMBED_COLOR_ALERT = _hex_color(os.getenv("EMBED_COLOR_ALERT", ""), 0xED4245)
EMBED_COLOR_WARN = _hex_color(os.getenv("EMBED_COLOR_WARN", ""), 0xFEE75C)
EMBED_FOOTER = os.getenv("EMBED_FOOTER", BOT_NAME)

EMOJIS_JSON_PATH = os.getenv("EMOJIS_JSON_PATH", "emojis.json")
UPLOADED_EMOJIS_JSON_PATH = os.getenv("UPLOADED_EMOJIS_JSON_PATH", "uploaded_emojis.json")
EMOJI_ASSETS_DIR = os.getenv("EMOJI_ASSETS_DIR", "assets/emojis")

ANTINUKE_NO_BYPASS_ROLE = os.getenv("ANTINUKE_NO_BYPASS_ROLE", "No-Bypass")
ANTINUKE_BARRIER_ROLE = os.getenv("ANTINUKE_BARRIER_ROLE", "Barrier ~ Unit")
ANTINUKE_DEFAULT_PUNISHMENT = os.getenv("ANTINUKE_DEFAULT_PUNISHMENT", "strip")



ANTINUKE_SELFBOT_WINDOW_SECONDS = int(os.getenv("ANTINUKE_SELFBOT_WINDOW_SECONDS", "5"))
ANTINUKE_SELFBOT_THRESHOLD = int(os.getenv("ANTINUKE_SELFBOT_THRESHOLD", "8"))

ANTINUKE_AUDIT_LOOKBACK_SECONDS = int(os.getenv("ANTINUKE_AUDIT_LOOKBACK_SECONDS", "5"))

ANTINUKE_DANGEROUS_PERMISSIONS = [
    "administrator",
    "ban_members",
    "kick_members",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "manage_nicknames",
    "mention_everyone",
]

ANTINUKE_EVENT_KEYS = [
    "antibot",
    "antiban",
    "antiunban",
    "antichannel",
    "antirole",
    "antiguildupdate",
    "antiroleupdate",
    "antidangerous",
    "antiwebhook",
    "antiselfbot",
]

ANTINUKE_EVENT_LABELS = {
    "antibot": "Bot Add",
    "antiban": "Mass/Unauthorized Ban",
    "antiunban": "Unauthorized Unban",
    "antichannel": "Channel Create/Delete",
    "antirole": "Role Create/Delete",
    "antiguildupdate": "Server Update",
    "antiroleupdate": "Role Update",
    "antidangerous": "Dangerous Permission Grant",
    "antiwebhook": "Webhook Abuse",
    "antiselfbot": "Message Flood / Selfbot",
}

MOD_LOG_FALLBACK_CHANNEL_NAME = os.getenv("MOD_LOG_FALLBACK_CHANNEL_NAME", "mod-logs")
DEFAULT_STICKER_EMOJI = os.getenv("DEFAULT_STICKER_EMOJI", "💀")

LAVALINK_HOST = os.getenv("LAVALINK_HOST", "")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", "2333"))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "")
LAVALINK_SECURE = os.getenv("LAVALINK_SECURE", "false").lower() == "true"

AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_API_BASE = os.getenv("AI_API_BASE", "https://api.openai.com/v1")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
