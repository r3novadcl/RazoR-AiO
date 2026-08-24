import aiohttp
from discord.ext import commands

from utils import embeds

ENDPOINTS = {
    "dog": "https://dog.ceo/api/breeds/image/random",
    "cat": "https://api.thecatapi.com/v1/images/search",
    "fox": "https://randomfox.ca/floof/",
    "duck": "https://random-d.uk/api/v2/random",
}


class Animals(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    async def _fetch(self, animal: str) -> str | None:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        try:
            async with self.session.get(ENDPOINTS[animal]) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if animal == "dog":
                    return data.get("message")
                if animal == "cat":
                    return data[0]["url"] if data else None
                if animal == "fox":
                    return data.get("image")
                if animal == "duck":
                    return data.get("url")
        except (aiohttp.ClientError, KeyError, IndexError):
            return None
        return None

    async def _send(self, ctx: commands.Context, animal: str):
        url = await self._fetch(animal)
        await ctx.send(view=embeds.image(f"Random {animal.capitalize()}", url, emoji_key="cat_animals"))

    @commands.hybrid_command(name="dog", description="Get a random dog picture")
    async def dog(self, ctx: commands.Context):
        await self._send(ctx, "dog")

    @commands.hybrid_command(name="cat", description="Get a random cat picture")
    async def cat(self, ctx: commands.Context):
        await self._send(ctx, "cat")

    @commands.hybrid_command(name="fox", description="Get a random fox picture")
    async def fox(self, ctx: commands.Context):
        await self._send(ctx, "fox")

    @commands.hybrid_command(name="duck", description="Get a random duck picture")
    async def duck(self, ctx: commands.Context):
        await self._send(ctx, "duck")

    async def cog_unload(self) -> None:
        if self.session:
            await self.session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(Animals(bot))
