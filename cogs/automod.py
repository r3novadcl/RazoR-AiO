import re
import time

import discord
from discord.ext import commands

import config
from utils import database
from utils import embeds
from utils import emojis
from cogs.ignore import is_ignored

INVITE_PATTERN = re.compile(r"(discord\.gg|discord(?:app)?\.com/invite)/\S+", re.IGNORECASE)
LINK_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


def status_block(cfg: dict) -> str:
    def flag(on: bool) -> str:
        return emojis.get("online", "🟢") if on else emojis.get("offline", "🔴")

    words = ", ".join(cfg["word_filter"][:15]) if cfg["word_filter"] else "None"
    return (
        f"{flag(cfg['anti_link'])} Anti-Link\n"
        f"{flag(cfg['anti_invite'])} Anti-Invite\n"
        f"{flag(cfg['anti_spam'])} Anti-Spam (`{cfg['spam_threshold']}` msgs / `{cfg['spam_window_seconds']}`s)\n"
        f"**Word filter ({len(cfg['word_filter'])}):** {words}"
    )


class WordFilterModal(discord.ui.Modal, title="Manage Word Filter"):
    words = discord.ui.TextInput(
        label="Filtered words (comma-separated)", style=discord.TextStyle.paragraph, required=False, max_length=1000
    )

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        raw = str(self.words.value)
        parsed = [w.strip().lower() for w in raw.split(",") if w.strip()]
        cfg = await database.set_automod_config(self.guild_id, word_filter=parsed)
        await interaction.response.edit_message(view=AutoModPanel(self.guild_id, cfg))


class ToggleButton(discord.ui.Button):
    def __init__(self, guild_id: int, field: str, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.guild_id = guild_id
        self.field = field

    async def callback(self, interaction: discord.Interaction):
        cfg = await database.get_automod_config(self.guild_id)
        cfg = await database.set_automod_config(self.guild_id, **{self.field: not cfg[self.field]})
        await interaction.response.edit_message(view=AutoModPanel(self.guild_id, cfg))


class WordFilterButton(discord.ui.Button):
    def __init__(self, guild_id: int):
        super().__init__(label="Manage Word Filter", style=discord.ButtonStyle.primary)
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(WordFilterModal(self.guild_id))


class AutoModPanel(discord.ui.LayoutView):
    def __init__(self, guild_id: int, cfg: dict):
        super().__init__(timeout=180)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(f"{emojis.get('shield', '🧹')} **Auto-Mod Dashboard**"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(status_block(cfg)))
        row1 = discord.ui.ActionRow()
        row1.add_item(ToggleButton(guild_id, "anti_link", "Toggle Anti-Link"))
        row1.add_item(ToggleButton(guild_id, "anti_invite", "Toggle Anti-Invite"))
        row1.add_item(ToggleButton(guild_id, "anti_spam", "Toggle Anti-Spam"))
        container.add_item(row1)
        row2 = discord.ui.ActionRow()
        row2.add_item(WordFilterButton(guild_id))
        container.add_item(row2)
        self.add_item(container)


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._spam_windows: dict[str, list[float]] = {}

    @commands.hybrid_group(name="automod", description="Configure automatic moderation", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @automod.command(name="panel", description="Open the auto-mod control dashboard")
    @commands.has_permissions(administrator=True)
    async def automod_panel(self, ctx: commands.Context):
        cfg = await database.get_automod_config(ctx.guild.id)
        await ctx.send(view=AutoModPanel(ctx.guild.id, cfg), ephemeral=True)

    @automod.command(name="antilink", description="Toggle link blocking")
    @commands.has_permissions(administrator=True)
    async def antilink(self, ctx: commands.Context, state: bool):
        await database.set_automod_config(ctx.guild.id, anti_link=state)
        await ctx.send(view=embeds.success("Anti-Link Updated", f"Now **{'ON' if state else 'OFF'}**"), ephemeral=True)

    @automod.command(name="antiinvite", description="Toggle Discord invite blocking")
    @commands.has_permissions(administrator=True)
    async def antiinvite(self, ctx: commands.Context, state: bool):
        await database.set_automod_config(ctx.guild.id, anti_invite=state)
        await ctx.send(view=embeds.success("Anti-Invite Updated", f"Now **{'ON' if state else 'OFF'}**"), ephemeral=True)

    @automod.command(name="antispam", description="Toggle message-spam blocking")
    @commands.has_permissions(administrator=True)
    async def antispam(self, ctx: commands.Context, state: bool):
        await database.set_automod_config(ctx.guild.id, anti_spam=state)
        await ctx.send(view=embeds.success("Anti-Spam Updated", f"Now **{'ON' if state else 'OFF'}**"), ephemeral=True)

    @automod.command(name="addword", description="Add a word to the filter")
    @commands.has_permissions(administrator=True)
    async def addword(self, ctx: commands.Context, *, word: str):
        cfg = await database.get_automod_config(ctx.guild.id)
        words = cfg["word_filter"]
        if word.lower() not in words:
            words.append(word.lower())
        await database.set_automod_config(ctx.guild.id, word_filter=words)
        await ctx.send(view=embeds.success("Word Filter Updated", f"Added `{word}`"), ephemeral=True)

    @automod.command(name="removeword", description="Remove a word from the filter")
    @commands.has_permissions(administrator=True)
    async def removeword(self, ctx: commands.Context, *, word: str):
        cfg = await database.get_automod_config(ctx.guild.id)
        words = [w for w in cfg["word_filter"] if w != word.lower()]
        await database.set_automod_config(ctx.guild.id, word_filter=words)
        await ctx.send(view=embeds.success("Word Filter Updated", f"Removed `{word}`"), ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if message.author.guild_permissions.manage_messages:
            return
        if await is_ignored(message.guild.id, message.author.id, message.channel.id):
            return

        cfg = await database.get_automod_config(message.guild.id)

        if cfg["anti_invite"] and INVITE_PATTERN.search(message.content):
            await self._strike(message, "Discord invite link detected")
            return

        if cfg["anti_link"] and LINK_PATTERN.search(message.content):
            await self._strike(message, "Link detected")
            return

        if cfg["word_filter"] and any(w in message.content.lower() for w in cfg["word_filter"]):
            await self._strike(message, "Filtered word detected")
            return

        if cfg["anti_spam"]:
            key = f"{message.guild.id}:{message.author.id}"
            now = time.time()
            window = [t for t in self._spam_windows.get(key, []) if now - t < cfg["spam_window_seconds"]]
            window.append(now)
            self._spam_windows[key] = window
            if len(window) >= cfg["spam_threshold"]:
                await self._strike(message, "Message spam detected")
                self._spam_windows[key] = []

    async def _strike(self, message: discord.Message, reason: str):
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        try:
            await message.channel.send(
                view=embeds.warning("Message Removed", f"{message.author.mention} — {reason}"), delete_after=6
            )
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMod(bot))
