import aiohttp
from discord.ext import commands

from utils import embeds

WAIFU_PICS_BASE = "https://api.waifu.pics/sfw"

CATEGORY_ENDPOINTS = {"anime": "waifu", "male": "waifu", "female": "waifu"}


class Pfps(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    async def _fetch(self, endpoint: str) -> str | None:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        try:
            async with self.session.get(f"{WAIFU_PICS_BASE}/{endpoint}") as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("url")
        except aiohttp.ClientError:
            return None

    async def _send_pfp(self, ctx: commands.Context, label: str):
        url = await self._fetch(CATEGORY_ENDPOINTS[label])
        await ctx.send(view=embeds.image(f"Random {label.capitalize()} PFP", url, emoji_key="cat_profiles"))

    @commands.hybrid_command(name="animepfp", description="Get a random anime profile picture")
    async def animepfp(self, ctx: commands.Context):
        await self._send_pfp(ctx, "anime")

    @commands.hybrid_command(name="malepfp", description="Get a random male profile picture")
    async def malepfp(self, ctx: commands.Context):
        await self._send_pfp(ctx, "male")

    @commands.hybrid_command(name="femalepfp", description="Get a random female profile picture")
    async def femalepfp(self, ctx: commands.Context):
        await self._send_pfp(ctx, "female")

    async def cog_unload(self) -> None:
        if self.session:
            await self.session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(Pfps(bot))
