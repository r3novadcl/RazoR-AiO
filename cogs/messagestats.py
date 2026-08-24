import discord
from discord.ext import commands

from utils import database
from utils import embeds


class MessageStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        await database.bump_message_count(message.guild.id, message.author.id)

    @commands.hybrid_command(name="messages", description="Check how many messages someone has sent")
    async def messages(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        rows = await database.get_message_leaderboard(ctx.guild.id, limit=1000)
        count = next((r["count"] for r in rows if r["user_id"] == target.id), 0)
        await ctx.send(view=embeds.info(f"{target.display_name}'s Messages", f"**{count}** messages sent"))

    @commands.hybrid_command(name="messagesleaderboard", description="Most active members in this server")
    async def messages_leaderboard(self, ctx: commands.Context):
        rows = await database.get_message_leaderboard(ctx.guild.id)
        if not rows:
            await ctx.send(view=embeds.info("No Data Yet"), ephemeral=True)
            return
        lines = [f"**#{i+1}** — <@{r['user_id']}> — {r['count']} messages" for i, r in enumerate(rows)]
        await ctx.send(view=embeds.SectionLayout("Message Leaderboard", lines))


async def setup(bot: commands.Bot):
    await bot.add_cog(MessageStats(bot))
