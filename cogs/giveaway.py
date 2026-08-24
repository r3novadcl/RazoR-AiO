import random
import time

import discord
from discord.ext import commands, tasks

import config
from utils import database
from utils import embeds
from utils import emojis


def parse_duration(raw: str) -> int:
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    raw = raw.strip().lower()
    if raw[-1] in units and raw[:-1].isdigit():
        return int(raw[:-1]) * units[raw[-1]]
    if raw.isdigit():
        return int(raw) * 60
    raise ValueError("Duration must look like 30s, 10m, 2h, or 1d")


class GiveawayEnterView(discord.ui.LayoutView):
    def __init__(self, giveaway_id: int, prize: str):
        super().__init__(timeout=None)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR_OK)
        container.add_item(discord.ui.TextDisplay(f"{emojis.get('party', '🎉')} **Giveaway: {prize}**\nClick below to enter!"))
        row = discord.ui.ActionRow()
        row.add_item(EnterButton(giveaway_id))
        container.add_item(row)
        self.add_item(container)


class EnterButton(discord.ui.Button):
    def __init__(self, giveaway_id: int):
        super().__init__(label="Enter", style=discord.ButtonStyle.success, custom_id=f"razor:giveaway:{giveaway_id}")
        self.giveaway_id = giveaway_id

    async def callback(self, interaction: discord.Interaction):
        await database.add_giveaway_entry(self.giveaway_id, interaction.user.id)
        await interaction.response.send_message(view=embeds.success("Entered!", f"Good luck {emojis.get('heart', '🍀')}"), ephemeral=True)


class Giveaway(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_giveaways.start()
        self._reregistered = False

    async def cog_load(self) -> None:
        if self._reregistered:
            return
        for giveaway in await database.get_active_giveaways():
            self.bot.add_view(GiveawayEnterView(giveaway["id"], giveaway["prize"]))
        self._reregistered = True

    def cog_unload(self) -> None:
        self.check_giveaways.cancel()

    @commands.hybrid_command(name="gstart", description="Start a giveaway")
    @commands.has_permissions(manage_guild=True)
    async def gstart(self, ctx: commands.Context, duration: str, winners: int, *, prize: str):
        try:
            seconds = parse_duration(duration)
        except ValueError as exc:
            await ctx.send(view=embeds.error("Invalid Duration", str(exc)), ephemeral=True)
            return

        end_time = time.time() + seconds
        message = await ctx.channel.send(view=embeds.info("Starting giveaway...", prize))
        giveaway_id = await database.create_giveaway(ctx.guild.id, ctx.channel.id, message.id, prize, winners, ctx.author.id, end_time)
        await message.edit(view=GiveawayEnterView(giveaway_id, prize))
        await ctx.send(view=embeds.success("Giveaway Started", prize), ephemeral=True)

    @commands.hybrid_command(name="gend", description="End a giveaway early")
    @commands.has_permissions(manage_guild=True)
    async def gend(self, ctx: commands.Context, message_id: str):
        giveaway = await database.get_giveaway_by_message(int(message_id))
        if giveaway is None or giveaway["ended"]:
            await ctx.send(view=embeds.error("Not Found", "No active giveaway with that message ID."), ephemeral=True)
            return
        await self._finish_giveaway(giveaway)
        await ctx.send(view=embeds.success("Giveaway Ended"), ephemeral=True)

    @commands.hybrid_command(name="greroll", description="Reroll a giveaway's winner")
    @commands.has_permissions(manage_guild=True)
    async def greroll(self, ctx: commands.Context, message_id: str):
        giveaway = await database.get_giveaway_by_message(int(message_id))
        if giveaway is None:
            await ctx.send(view=embeds.error("Not Found", "No giveaway with that message ID."), ephemeral=True)
            return
        entries = await database.get_giveaway_entries(giveaway["id"])
        if not entries:
            await ctx.send(view=embeds.warning("No Entries", "Nobody entered this giveaway."), ephemeral=True)
            return
        winner_id = random.choice(entries)
        await ctx.send(view=embeds.success("New Winner", f"<@{winner_id}> — {giveaway['prize']}"))

    @commands.hybrid_command(name="glist", description="List all active giveaways in this server")
    async def glist(self, ctx: commands.Context):
        rows = await database.get_active_giveaways_for_guild(ctx.guild.id)
        if not rows:
            await ctx.send(view=embeds.info("No Active Giveaways"), ephemeral=True)
            return
        lines = [
            f"**{r['prize']}** — <#{r['channel_id']}> • ends <t:{int(r['end_time'])}:R> • message `{r['message_id']}`"
            for r in rows
        ]
        await ctx.send(view=embeds.SectionLayout(f"{emojis.get('party', '🎉')} Active Giveaways", lines), ephemeral=True)

    async def _finish_giveaway(self, giveaway: dict) -> None:
        await database.end_giveaway(giveaway["id"])
        entries = await database.get_giveaway_entries(giveaway["id"])
        guild = self.bot.get_guild(giveaway["guild_id"])
        channel = guild.get_channel(giveaway["channel_id"]) if guild else None

        winner_count = min(giveaway["winner_count"], len(entries)) if entries else 0
        winners = random.sample(entries, winner_count) if winner_count else []

        if channel:
            try:
                message = await channel.fetch_message(giveaway["message_id"])
                await message.edit(view=embeds.info(f"{emojis.get('party', '🎉')} Giveaway Ended: {giveaway['prize']}", "This giveaway has ended."))
            except discord.HTTPException:
                pass

            if winners:
                mentions = ", ".join(f"<@{w}>" for w in winners)
                await channel.send(view=embeds.success("Winners!", f"{mentions} — you won **{giveaway['prize']}**!"))
            else:
                await channel.send(view=embeds.warning("No Winners", "Nobody entered this giveaway."))

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        for giveaway in await database.get_active_giveaways():
            if time.time() >= giveaway["end_time"]:
                await self._finish_giveaway(giveaway)

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
