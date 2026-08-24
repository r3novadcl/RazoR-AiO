import platform
import sys

import discord
from discord.ext import commands

import config
from utils import embeds

try:
    import resource
except ImportError:
    resource = None


def format_uptime(delta) -> str:
    seconds = int(delta.total_seconds())
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def memory_usage_mb() -> float | None:
    if resource is None:
        return None
    kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return kb / (1024 * 1024) if sys.platform == "darwin" else kb / 1024


class StatsInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="stats", description="Detailed bot statistics")
    async def stats(self, ctx: commands.Context):
        bot = self.bot
        uptime = format_uptime(discord.utils.utcnow() - bot.start_time)
        command_count = sum(1 for _ in bot.walk_commands())
        total_members = sum(g.member_count or 0 for g in bot.guilds)
        total_channels = sum(len(g.channels) for g in bot.guilds)
        mem_mb = memory_usage_mb()

        overview = (
            f"**Servers:** {len(bot.guilds)}\n"
            f"**Users:** {total_members:,}\n"
            f"**Channels:** {total_channels:,}\n"
            f"**Uptime:** {uptime}"
        )
        performance = (
            f"**Latency:** {round(bot.latency * 1000)}ms\n"
            f"**Commands:** {command_count} across {len(bot.cogs)} modules\n"
            + (f"**Memory:** {mem_mb:.1f} MB\n" if mem_mb is not None else "")
        )
        environment = (
            f"**Python:** {platform.python_version()}\n"
            f"**discord.py:** {discord.__version__}\n"
            f"**Platform:** {platform.system()}"
        )

        view = embeds.SectionLayout(
            f"{config.BOT_NAME} Statistics",
            [overview, performance, environment],
            emoji_key="chart",
        )
        await ctx.send(view=view)

    @commands.hybrid_command(name="roleinfo", description="Information about a role")
    async def roleinfo(self, ctx: commands.Context, role: discord.Role):
        view = embeds.SectionLayout(
            f"@{role.name}",
            [
                f"**ID:** `{role.id}`\n**Members:** {len(role.members)}\n**Colour:** `{role.colour}`",
                f"**Hoisted:** {role.hoist}\n**Mentionable:** {role.mentionable}\n**Created:** {discord.utils.format_dt(role.created_at, 'R')}",
            ],
        )
        await ctx.send(view=view)

    @commands.hybrid_command(name="listchannels", description="List all channels in this server")
    async def listchannels(self, ctx: commands.Context):
        categories = [c for c in ctx.guild.channels if isinstance(c, discord.CategoryChannel)]
        lines = []
        for cat in categories:
            children = ", ".join(f"#{ch.name}" for ch in cat.channels[:10])
            lines.append(f"**{cat.name}**\n{children or '(empty)'}")
        uncategorized = [c.name for c in ctx.guild.channels if c.category is None and not isinstance(c, discord.CategoryChannel)]
        if uncategorized:
            lines.append(f"**No Category**\n{', '.join(uncategorized[:10])}")
        await ctx.send(view=embeds.SectionLayout(f"Channels — {ctx.guild.name}", lines or ["No channels found."]))

    @commands.hybrid_command(name="emojiinfo", description="Information about a custom emoji")
    async def emojiinfo(self, ctx: commands.Context, emoji: discord.Emoji):
        view = embeds.SectionLayout(
            f":{emoji.name}:",
            [f"**ID:** `{emoji.id}`\n**Animated:** {emoji.animated}\n**Created:** {discord.utils.format_dt(emoji.created_at, 'R')}\n**URL:** {emoji.url}"],
        )
        await ctx.send(view=view)

    @commands.hybrid_command(name="joinpos", description="See a member's join position in this server")
    async def joinpos(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        members = sorted(ctx.guild.members, key=lambda m: m.joined_at or ctx.guild.created_at)
        try:
            position = members.index(target) + 1
        except ValueError:
            position = "unknown"
        await ctx.send(view=embeds.info(f"{target.display_name}'s Join Position", f"**#{position}** out of {len(members)} members"))

    @commands.hybrid_command(name="firstjoins", description="See the first members to join this server")
    async def firstjoins(self, ctx: commands.Context, amount: commands.Range[int, 1, 25] = 10):
        members = sorted(ctx.guild.members, key=lambda m: m.joined_at or ctx.guild.created_at)[:amount]
        lines = [f"**#{i+1}** {m.mention} — {discord.utils.format_dt(m.joined_at, 'R') if m.joined_at else 'unknown'}" for i, m in enumerate(members)]
        await ctx.send(view=embeds.SectionLayout("First to Join", lines))

    @commands.hybrid_command(name="rolecall", description="List all members with a specific role")
    async def rolecall(self, ctx: commands.Context, role: discord.Role):
        members = role.members[:40]
        if not members:
            await ctx.send(view=embeds.info("No Members", f"Nobody has {role.mention}."), ephemeral=True)
            return
        lines = [m.mention for m in members]
        extra = f"\n...and {len(role.members) - 40} more" if len(role.members) > 40 else ""
        await ctx.send(view=embeds.SectionLayout(f"Members with @{role.name}", ["\n".join(lines) + extra]))


async def setup(bot: commands.Bot):
    await bot.add_cog(StatsInfo(bot))
