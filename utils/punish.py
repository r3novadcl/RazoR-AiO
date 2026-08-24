import discord

import config
from utils import database
from utils import embeds


def has_dangerous_perms(perms: discord.Permissions) -> bool:
    return any(getattr(perms, name, False) for name in config.ANTINUKE_DANGEROUS_PERMISSIONS)


def is_immune(guild: discord.Guild, cfg: dict, member: discord.Member | None) -> bool:
    if member is None:
        return True  # unresolved executor — never punish blindly
    if member.id == guild.owner_id:
        return True
    if guild.me and member.id == guild.me.id:
        return True
    if member.id in cfg["extraowners"]:
        return True
    if member.id in cfg["whitelist"]:
        return True

    no_bypass_id = cfg.get("no_bypass_role_id")
    if no_bypass_id and any(r.id == no_bypass_id for r in member.roles):
        return False  # explicitly excluded from immunity even if they also hold a mainrole

    return any(role_id in [r.id for r in member.roles] for role_id in cfg["mainroles"])


async def log_action(guild: discord.Guild, view: discord.ui.LayoutView) -> None:
    cfg = database.get_antinuke_config(guild.id)
    channel_id = cfg.get("log_channel")
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel is None:
        return
    try:
        await channel.send(view=view)
    except discord.HTTPException:
        pass


async def punish(guild: discord.Guild, member: discord.Member, reason: str) -> None:
    cfg = database.get_antinuke_config(guild.id)
    mode = cfg.get("punishment", config.ANTINUKE_DEFAULT_PUNISHMENT)
    try:
        if mode == "ban":
            await guild.ban(member, reason=f"Anti-Nuke: {reason}")
        elif mode == "kick":
            await member.kick(reason=f"Anti-Nuke: {reason}")
        else:
            roles_to_strip = [r for r in member.roles if r != guild.default_role]
            if roles_to_strip:
                await member.remove_roles(*roles_to_strip, reason=f"Anti-Nuke: {reason}")
            barrier_id = cfg.get("barrier_role_id")
            if barrier_id:
                role = guild.get_role(barrier_id)
                if role:
                    await member.add_roles(role, reason=f"Anti-Nuke quarantine: {reason}")
    except discord.Forbidden:
        pass


async def handle_violation(guild: discord.Guild, event_key: str, executor, detail: str) -> None:
    if guild.id not in database._antinuke_cache:
        await database.refresh_antinuke(guild.id)
    cfg = database.get_antinuke_config(guild.id)

    if not cfg["enabled"] or not cfg["events"].get(event_key, True):
        return
    if executor is None:
        return

    member = guild.get_member(executor.id)
    if member is None:
        try:
            member = await guild.fetch_member(executor.id)
        except discord.HTTPException:
            member = None

    if is_immune(guild, cfg, member):
        return

    await punish(guild, member, detail)
    await database.bump_antinuke_stat(guild.id, event_key)

    view = embeds.alert(
        "Threat Neutralized",
        f"**Trigger:** {detail}\n"
        f"**User:** {member.mention} (`{member.id}`)\n"
        f"**Action taken:** {cfg['punishment']}\n"
        f"**Category:** {config.ANTINUKE_EVENT_LABELS.get(event_key, event_key)}",
    )
    await log_action(guild, view)


async def alert_unresolved(guild: discord.Guild, event_key: str, detail: str) -> None:
    """Protection is on but the audit log gave us no executor — usually a
    webhook, integration, or raw API token. We can't punish an unknown
    actor safely, but silently ignoring this defeats the point, so it's
    always surfaced to the log channel."""
    if guild.id not in database._antinuke_cache:
        await database.refresh_antinuke(guild.id)
    cfg = database.get_antinuke_config(guild.id)
    if not cfg["enabled"] or not cfg["events"].get(event_key, True):
        return
    view = embeds.alert(
        "Unresolved Actor",
        f"**Trigger:** {detail}\nCouldn't attribute this to a member from the audit log "
        "(often a webhook, integration, or raw API token). Review recent integrations/webhooks manually.",
    )
    await log_action(guild, view)
