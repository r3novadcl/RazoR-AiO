import asyncio
import base64
import logging

import discord
from discord.ext import commands

import config
from utils import database
from utils import emojis
from utils.checks import handle_app_command_error, handle_command_error
from utils.emoji_sync import sync_application_emojis

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger(config.BOT_NAME)

INITIAL_COGS = (
    "cogs.antinuke_events",
    "cogs.antinuke_commands",
    "cogs.antiraid",
    "cogs.moderation",
    "cogs.utility",
    "cogs.fun",
    "cogs.roleplay",
    "cogs.welcome_leave",
    "cogs.automod",
    "cogs.tickets",
    "cogs.giveaway",
    "cogs.logging_cog",
    "cogs.leveling",
    "cogs.reactionroles",
    "cogs.j2c",
    "cogs.vanityroles",
    "cogs.autoresponder",
    "cogs.mention",
    "cogs.music",
    "cogs.owner_tools",
    "cogs.todo",
    "cogs.remind",
    "cogs.invites",
    "cogs.messagestats",
    "cogs.stats_info",
    "cogs.conversion",
    "cogs.ignore",
    "cogs.pfps",
    "cogs.animals",
    "cogs.github",
    "cogs.steal",
    "cogs.autoreact",
    "cogs.autopost",
    "cogs.ai",
    "cogs.google",
    "cogs.youtube",
    "cogs.tts",
    "cogs.profile",
    "cogs.help",
)


def _decode_client_id(token: str) -> str | None:
    try:
        segment = token.split(".")[0]
        padded = segment + "=" * (-len(segment) % 4)
        decoded = base64.b64decode(padded).decode("utf-8")
        return decoded if decoded.isdigit() else None
    except Exception:
        return None


def resolve_prefix(bot: commands.Bot, message: discord.Message) -> str:
    guild_id = message.guild.id if message.guild else None
    return database.get_cached_prefix(guild_id, config.PREFIX)


class RazoR(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.moderation = True
        intents.presences = True
        super().__init__(command_prefix=resolve_prefix, intents=intents, help_command=None)
        self.start_time = discord.utils.utcnow()

    async def setup_hook(self) -> None:
        await database.connect()
        await database.warm_prefix_cache()
        emojis.load()
        self._ready_once = False

        for extension in INITIAL_COGS:
            await self.load_extension(extension)

        self.tree.on_error = handle_app_command_error

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        await handle_command_error(ctx, error)

    async def on_ready(self) -> None:
        log.info(f"Logged in as {self.user} ({self.user.id}) — {config.BOT_NAME}")

        activity_icon = emojis.get("shield", "🛡️")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"FX DEVELOPMENT | RazoR"))

        if self._ready_once:
            return
        self._ready_once = True

        client_id = config.CLIENT_ID or _decode_client_id(config.TOKEN) or str(self.user.id)
        try:
            await sync_application_emojis(client_id, config.TOKEN, log=log.info)
            emojis.load()
        except Exception as exc:
            log.warning(f"Emoji sync skipped: {exc}")

        await database.warm_antinuke_cache([g.id for g in self.guilds])

        try:
            synced = await self.tree.sync()
            log.info(f"Synced {len(synced)} slash command(s).")
        except discord.HTTPException as exc:
            log.warning(f"Command sync failed: {exc}")

    async def on_guild_join(self, guild: discord.Guild) -> None:
        await database.refresh_antinuke(guild.id)


async def main():
    if not config.TOKEN:
        raise SystemExit("TOKEN is missing — change your token in config.py.")

    bot = RazoR()
    try:
        await bot.start(config.TOKEN)
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
