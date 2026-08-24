import discord
from discord.ext import commands

from utils import database
from utils import embeds
from utils import emojis
from cogs.ignore import is_ignored


class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="leveling", description="Configure the XP/leveling system", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def leveling(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @leveling.command(name="enable", description="Enable leveling")
    @commands.has_permissions(administrator=True)
    async def leveling_enable(self, ctx: commands.Context):
        await database.set_leveling_config(ctx.guild.id, enabled=True)
        await ctx.send(view=embeds.success("Leveling Enabled"), ephemeral=True)

    @leveling.command(name="disable", description="Disable leveling")
    @commands.has_permissions(administrator=True)
    async def leveling_disable(self, ctx: commands.Context):
        await database.set_leveling_config(ctx.guild.id, enabled=False)
        await ctx.send(view=embeds.warning("Leveling Disabled"), ephemeral=True)

    @leveling.command(name="announcechannel", description="Set the level-up announcement channel")
    @commands.has_permissions(administrator=True)
    async def leveling_announcechannel(self, ctx: commands.Context, channel: discord.TextChannel):
        await database.set_leveling_config(ctx.guild.id, announce_channel_id=channel.id)
        await ctx.send(view=embeds.success("Announce Channel Set", channel.mention), ephemeral=True)

    @leveling.command(name="status", description="View the current leveling configuration")
    async def leveling_status(self, ctx: commands.Context):
        cfg = await database.get_leveling_config(ctx.guild.id)
        channel = ctx.guild.get_channel(cfg["announce_channel_id"]) if cfg["announce_channel_id"] else None
        state = emojis.get("online", "🟢") + " Enabled" if cfg["enabled"] else emojis.get("offline", "🔴") + " Disabled"
        await ctx.send(view=embeds.info("Leveling Status", f"**Status:** {state}\n**Announce channel:** {channel.mention if channel else 'Current channel (default)'}"), ephemeral=True)

    @commands.hybrid_command(name="rank", description="Check your (or someone's) rank")
    async def rank(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        row = await database.get_rank(ctx.guild.id, target.id)
        if row is None:
            await ctx.send(view=embeds.info("No XP Yet", f"{target.mention} hasn't earned any XP yet."), ephemeral=True)
            return
        next_level_xp = database.xp_for_level(row["level"] + 1)
        await ctx.send(view=embeds.info(f"{target.display_name}'s Rank", f"**Level:** {row['level']}\n**XP:** {row['xp']} / {next_level_xp}"))

    @commands.hybrid_command(name="leaderboard", description="Show the server XP leaderboard")
    async def leaderboard(self, ctx: commands.Context):
        rows = await database.get_leaderboard(ctx.guild.id)
        if not rows:
            await ctx.send(view=embeds.info("Leaderboard Empty", "Nobody has earned XP yet."), ephemeral=True)
            return
        lines = [f"**#{i+1}** — <@{r['user_id']}> — Level {r['level']} ({r['xp']} XP)" for i, r in enumerate(rows)]
        await ctx.send(view=embeds.SectionLayout("Leaderboard", lines))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        cfg = await database.get_leveling_config(message.guild.id)
        if not cfg["enabled"]:
            return
        if await is_ignored(message.guild.id, message.author.id, message.channel.id):
            return

        xp, level, leveled_up = await database.add_xp(message.guild.id, message.author.id, amount=15)
        if not leveled_up:
            return

        announce_id = cfg.get("announce_channel_id")
        channel = message.guild.get_channel(announce_id) if announce_id else message.channel
        if channel is None:
            return
        try:
            await channel.send(view=embeds.success("Level Up!", f"{message.author.mention} reached **level {level}**! {emojis.get('party', '🎉')}"))
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))
