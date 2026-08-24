from datetime import datetime, timezone

import discord

import config


async def find_executor(
    guild: discord.Guild,
    action: discord.AuditLogAction,
    target_id: int | None,
    within_seconds: int | None = None,
) -> discord.User | discord.Member | None:
    """Cross-references the audit log to find who actually performed an
    action, since several gateway events (channel_delete, role_delete, ...)
    don't carry the executor natively."""
    window = within_seconds or config.ANTINUKE_AUDIT_LOOKBACK_SECONDS
    try:
        async for entry in guild.audit_logs(action=action, limit=5):
            age = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
            if age > window:
                continue
            entry_target_id = getattr(entry.target, "id", None)
            if target_id is None or entry_target_id == target_id:
                return entry.user
        return None
    except (discord.Forbidden, discord.HTTPException):
        return None
