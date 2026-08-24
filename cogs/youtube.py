import aiohttp
import discord
from discord.ext import commands, tasks

import config
from utils import database
from utils import embeds
from utils import emojis

API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTube(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        if config.YOUTUBE_API_KEY:
            self.check_uploads.start()

    def cog_unload(self) -> None:
        if config.YOUTUBE_API_KEY:
            self.check_uploads.cancel()

    @commands.hybrid_group(name="youtube", description="Get notified when a YouTube channel uploads", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def youtube(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @youtube.command(name="add", description="Watch a YouTube channel for new uploads")
    @commands.has_permissions(administrator=True)
    async def youtube_add(self, ctx: commands.Context, youtube_channel_id: str, announce_channel: discord.TextChannel):
        if not config.YOUTUBE_API_KEY:
            await ctx.send(view=embeds.warning("YouTube Not Configured", "Set `YOUTUBE_API_KEY` in `.env` to enable this."), ephemeral=True)
            return
        await database.set_youtube_config(ctx.guild.id, announce_channel.id, youtube_channel_id)
        await ctx.send(view=embeds.success("Watching Channel", f"`{youtube_channel_id}` → {announce_channel.mention}"), ephemeral=True)

    @youtube.command(name="remove", description="Stop watching a YouTube channel")
    @commands.has_permissions(administrator=True)
    async def youtube_remove(self, ctx: commands.Context, youtube_channel_id: str):
        await database.remove_youtube_config(ctx.guild.id, youtube_channel_id)
        await ctx.send(view=embeds.success("Removed", youtube_channel_id), ephemeral=True)

    async def _latest_video(self, channel_id: str) -> dict | None:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        params = {
            "key": config.YOUTUBE_API_KEY, "channelId": channel_id, "part": "snippet",
            "order": "date", "maxResults": 1, "type": "video",
        }
        try:
            async with self.session.get(f"{API_BASE}/search", params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                items = data.get("items", [])
                return items[0] if items else None
        except aiohttp.ClientError:
            return None

    @tasks.loop(minutes=10)
    async def check_uploads(self):
        for entry in await database.get_youtube_configs():
            video = await self._latest_video(entry["youtube_channel_id"])
            if video is None:
                continue
            video_id = video["id"]["videoId"]
            if video_id == entry["last_video_id"]:
                continue

            channel = self.bot.get_channel(entry["announce_channel_id"])
            if channel:
                title = video["snippet"]["title"]
                url = f"https://youtube.com/watch?v={video_id}"
                try:
                    await channel.send(view=embeds.success(f"{emojis.get('tv', '📺')} New Upload!", f"**{title}**\n{url}"))
                except discord.HTTPException:
                    pass
            await database.update_youtube_last_video(entry["guild_id"], entry["youtube_channel_id"], video_id)

    @check_uploads.before_loop
    async def before_check_uploads(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(YouTube(bot))
