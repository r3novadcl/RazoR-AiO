import time

import discord
from discord.ext import commands

import config
from utils.audit import find_executor
from utils.punish import handle_violation, alert_unresolved, has_dangerous_perms, log_action
from utils import database
from utils import embeds


class AntiNukeEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._message_windows: dict[str, list[float]] = {}

    async def _cfg(self, guild_id: int) -> dict:
        if guild_id not in database._antinuke_cache:
            await database.refresh_antinuke(guild_id)
        return database.get_antinuke_config(guild_id)

    async def _protect_core_role(self, guild: discord.Guild, role_name: str, colour: discord.Colour, config_key: str):
        """No-Bypass and Barrier ~ Unit are load-bearing — recreated
        immediately if missing, regardless of who deleted them or whether
        antirole protection is even toggled on for the guild."""
        cfg = await self._cfg(guild.id)
        role_id = cfg.get(config_key)
        if role_id and guild.get_role(role_id):
            return
        new_role = await guild.create_role(name=role_name, colour=colour, reason="Anti-Nuke self-heal: core role missing")
        await database.save_antinuke_core(guild.id, **{config_key: new_role.id})
        await log_action(
            guild,
            embeds.alert("Core Role Restored", f"**@{role_name}** was missing and has been recreated automatically."),
        )

    # ---- antichannel ----
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        executor = await find_executor(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        if executor is None:
            await alert_unresolved(channel.guild, "antichannel", f"Deleted channel #{channel.name}")
            return
        await handle_violation(channel.guild, "antichannel", executor, f"Deleted channel #{channel.name}")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        executor = await find_executor(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        await handle_violation(channel.guild, "antichannel", executor, f"Created channel #{channel.name}")

    # ---- antiwebhook ----
    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        executor = await find_executor(channel.guild, discord.AuditLogAction.webhook_create, None, within_seconds=8)
        await handle_violation(channel.guild, "antiwebhook", executor, f"Webhook activity in #{channel.name}")

    # ---- antirole ----
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        guild = role.guild
        executor = await find_executor(guild, discord.AuditLogAction.role_delete, role.id)
        if executor is None:
            await alert_unresolved(guild, "antirole", f"Deleted role @{role.name}")
        else:
            await handle_violation(guild, "antirole", executor, f"Deleted role @{role.name}")

        if role.name == config.ANTINUKE_NO_BYPASS_ROLE:
            await self._protect_core_role(guild, config.ANTINUKE_NO_BYPASS_ROLE, discord.Colour.red(), "no_bypass_role_id")
        elif role.name == config.ANTINUKE_BARRIER_ROLE:
            await self._protect_core_role(guild, config.ANTINUKE_BARRIER_ROLE, discord.Colour.greyple(), "barrier_role_id")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        executor = await find_executor(role.guild, discord.AuditLogAction.role_create, role.id)
        await handle_violation(role.guild, "antirole", executor, f"Created role @{role.name}")

    # ---- antiroleupdate + antidangerous (role permission escalation) ----
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        guild = after.guild
        executor = await find_executor(guild, discord.AuditLogAction.role_update, after.id)

        gained_dangerous = has_dangerous_perms(after.permissions) and not has_dangerous_perms(before.permissions)
        if gained_dangerous:
            await handle_violation(guild, "antidangerous", executor, f"Granted dangerous permissions to role @{after.name}")
            return

        if before.name != after.name or before.colour != after.colour or before.hoist != after.hoist:
            await handle_violation(guild, "antiroleupdate", executor, f"Modified role @{after.name}")

    # ---- antidangerous (member directly given a dangerous role) ----
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        added_roles = [r for r in after.roles if r not in before.roles]
        if not added_roles:
            return
        dangerous_role = next((r for r in added_roles if has_dangerous_perms(r.permissions)), None)
        if dangerous_role is None:
            return
        executor = await find_executor(after.guild, discord.AuditLogAction.member_role_update, after.id)
        await handle_violation(after.guild, "antidangerous", executor, f"Gave dangerous role @{dangerous_role.name} to {after}")

    # ---- antiban / antiunban ----
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        executor = await find_executor(guild, discord.AuditLogAction.ban, user.id)
        if executor is None:
            await alert_unresolved(guild, "antiban", f"Banned {user}")
            return
        await handle_violation(guild, "antiban", executor, f"Banned {user}")

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        executor = await find_executor(guild, discord.AuditLogAction.unban, user.id)
        await handle_violation(guild, "antiunban", executor, f"Unbanned {user}")

    # ---- antiguildupdate ----
    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        executor = await find_executor(after, discord.AuditLogAction.guild_update, after.id)
        changes = []
        if before.name != after.name:
            changes.append(f"name: {before.name} -> {after.name}")
        if before.icon != after.icon:
            changes.append("icon changed")
        if before.vanity_url_code != after.vanity_url_code:
            changes.append("vanity URL changed")
        if before.owner_id != after.owner_id:
            changes.append("ownership transferred")
        if not changes:
            return
        detail = f"Guild updated ({', '.join(changes)})"
        if executor is None:
            await alert_unresolved(after, "antiguildupdate", detail)
            return
        await handle_violation(after, "antiguildupdate", executor, detail)

    # ---- antibot ----
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild

        if member.bot:
            executor = await find_executor(guild, discord.AuditLogAction.bot_add, member.id)
            await handle_violation(guild, "antibot", executor, f"Bot {member} added to server")

    # ---- antiselfbot: message-burst heuristic ----
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        cfg = await self._cfg(message.guild.id)
        if not (cfg["enabled"] and cfg["events"].get("antiselfbot", True)):
            return

        key = f"{message.guild.id}:{message.author.id}"
        now = time.time()
        window = [t for t in self._message_windows.get(key, []) if now - t < config.ANTINUKE_SELFBOT_WINDOW_SECONDS]
        window.append(now)
        self._message_windows[key] = window

        if len(window) > config.ANTINUKE_SELFBOT_THRESHOLD:
            member = message.guild.get_member(message.author.id)
            await handle_violation(message.guild, "antiselfbot", member, "Automated / selfbot-like message flooding detected")
            self._message_windows[key] = []


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiNukeEvents(bot))
