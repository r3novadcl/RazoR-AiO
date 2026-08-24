import json
import time

import discord

from utils import database


async def lockdown_guild(guild: discord.Guild, reason: str) -> int:
    everyone = guild.default_role
    backup = {}
    locked = 0

    for channel in guild.text_channels:
        overwrite = channel.overwrites_for(everyone)
        backup[str(channel.id)] = {"send_messages": overwrite.send_messages}
        overwrite.send_messages = False
        try:
            await channel.set_permissions(everyone, overwrite=overwrite, reason=reason)
            locked += 1
        except discord.Forbidden:
            pass

    for channel in guild.voice_channels:
        overwrite = channel.overwrites_for(everyone)
        backup[f"v{channel.id}"] = {"connect": overwrite.connect}
        overwrite.connect = False
        try:
            await channel.set_permissions(everyone, overwrite=overwrite, reason=reason)
            locked += 1
        except discord.Forbidden:
            pass

    await database.start_lockdown(guild.id, json.dumps(backup), time.time())
    return locked


async def unlock_guild(guild: discord.Guild) -> int:
    entry = await database.get_lockdown(guild.id)
    if entry is None:
        return 0

    backup = json.loads(entry["backup_json"])
    everyone = guild.default_role
    restored = 0

    for key, saved in backup.items():
        is_voice = key.startswith("v")
        channel_id = int(key[1:] if is_voice else key)
        channel = guild.get_channel(channel_id)
        if channel is None:
            continue
        overwrite = channel.overwrites_for(everyone)
        if is_voice:
            overwrite.connect = saved.get("connect")
        else:
            overwrite.send_messages = saved.get("send_messages")
        try:
            await channel.set_permissions(everyone, overwrite=overwrite, reason="Anti-Raid lockdown lifted")
            restored += 1
        except discord.Forbidden:
            pass

    await database.end_lockdown(guild.id)
    return restored


async def notify_owner_and_extraowners(guild: discord.Guild, title: str, description: str) -> None:
    from utils import embeds

    recipients = []
    if guild.owner:
        recipients.append(guild.owner)

    if guild.id in database._antinuke_cache:
        cfg = database.get_antinuke_config(guild.id)
        for uid in cfg.get("extraowners", []):
            member = guild.get_member(uid)
            if member:
                recipients.append(member)

    for user in recipients:
        try:
            await user.send(view=embeds.alert(title, f"**Server:** {guild.name}\n{description}"))
        except discord.HTTPException:
            pass
