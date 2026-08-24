import discord
from discord.ext import commands

from utils import database
from utils import embeds


class Invites(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cache: dict[int, dict[str, int]] = {}

    async def cog_load(self) -> None:
        for guild in self.bot.guilds:
            await self._cache_guild(guild)

    async def _cache_guild(self, guild: discord.Guild) -> None:
        try:
            invites = await guild.invites()
            self._cache[guild.id] = {inv.code: inv.uses or 0 for inv in invites}
        except discord.Forbidden:
            self._cache[guild.id] = {}

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self._cache_guild(guild)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        self._cache.setdefault(invite.guild.id, {})[invite.code] = invite.uses or 0

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        self._cache.get(invite.guild.id, {}).pop(invite.code, None)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        before = self._cache.get(guild.id, {})
        try:
            current = await guild.invites()
        except discord.Forbidden:
            return

        used_invite = None
        for invite in current:
            if invite.uses and invite.uses > before.get(invite.code, 0):
                used_invite = invite
                break

        self._cache[guild.id] = {inv.code: inv.uses or 0 for inv in current}

        if used_invite and used_invite.inviter:
            await database.add_invite_credit(guild.id, used_invite.inviter.id, 1)

    @commands.hybrid_command(name="invites", description="Check how many members someone has invited")
    async def invites_cmd(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        rows = await database.get_invite_leaderboard(ctx.guild.id, limit=1000)
        count = next((r["count"] for r in rows if r["user_id"] == target.id), 0)
        await ctx.send(view=embeds.info(f"{target.display_name}'s Invites", f"**{count}** members invited"))

    @commands.hybrid_command(name="invitesleaderboard", description="Top inviters in this server")
    async def invites_leaderboard(self, ctx: commands.Context):
        rows = await database.get_invite_leaderboard(ctx.guild.id)
        if not rows:
            await ctx.send(view=embeds.info("No Data Yet"), ephemeral=True)
            return
        lines = [f"**#{i+1}** — <@{r['user_id']}> — {r['count']} invites" for i, r in enumerate(rows)]
        await ctx.send(view=embeds.SectionLayout("Invite Leaderboard", lines))


async def setup(bot: commands.Bot):
    await bot.add_cog(Invites(bot))
