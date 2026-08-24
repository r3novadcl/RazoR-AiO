import time

import discord
from discord.ext import commands, tasks

from utils import database
from utils import embeds


class AutoPost(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.post_loop.start()

    def cog_unload(self) -> None:
        self.post_loop.cancel()

    @commands.hybrid_group(name="autopost", description="Schedule a message to repeat on an interval", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def autopost(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @autopost.command(name="add", description="Add a scheduled post (interval in minutes)")
    @commands.has_permissions(administrator=True)
    async def autopost_add(self, ctx: commands.Context, channel: discord.TextChannel, interval_minutes: int, *, content: str):
        entry_id = await database.add_autopost(ctx.guild.id, channel.id, content, interval_minutes)
        await ctx.send(view=embeds.success("Autopost Added", f"`#{entry_id}` every {interval_minutes}m in {channel.mention}"), ephemeral=True)

    @autopost.command(name="remove", description="Remove a scheduled post by ID")
    @commands.has_permissions(administrator=True)
    async def autopost_remove(self, ctx: commands.Context, entry_id: int):
        await database.remove_autopost(ctx.guild.id, entry_id)
        await ctx.send(view=embeds.success("Autopost Removed", f"`#{entry_id}`"), ephemeral=True)

    @autopost.command(name="list", description="List all scheduled posts")
    async def autopost_list(self, ctx: commands.Context):
        rows = await database.get_autoposts(ctx.guild.id)
        if not rows:
            await ctx.send(view=embeds.info("No Autoposts"), ephemeral=True)
            return
        lines = [f"`#{r['id']}` <#{r['channel_id']}> every {r['interval_minutes']}m" for r in rows]
        await ctx.send(view=embeds.SectionLayout("Autoposts", lines), ephemeral=True)

    @autopost.command(name="reset", description="Remove all scheduled posts")
    @commands.has_permissions(administrator=True)
    async def autopost_reset(self, ctx: commands.Context):
        await database.clear_autoposts(ctx.guild.id)
        await ctx.send(view=embeds.success("Autoposts Cleared"), ephemeral=True)

    @tasks.loop(minutes=1)
    async def post_loop(self):
        now = time.time()
        for entry in await database.get_autoposts():
            if now - entry["last_posted_at"] < entry["interval_minutes"] * 60:
                continue
            channel = self.bot.get_channel(entry["channel_id"])
            if channel is None:
                continue
            try:
                await channel.send(entry["content"])
                await database.touch_autopost(entry["id"])
            except discord.HTTPException:
                pass

    @post_loop.before_loop
    async def before_post_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoPost(bot))
