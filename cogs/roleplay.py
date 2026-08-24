import aiohttp
import discord
from discord.ext import commands

from utils import embeds

NEKOS_BEST_BASE = "https://nekos.best/api/v2"

VERBS = {
    "hug": "hugs", "kiss": "kisses", "pat": "pats", "slap": "slaps", "cuddle": "cuddles",
    "poke": "pokes", "tickle": "tickles", "bite": "bites", "highfive": "high-fives", "wave": "waves at",
}


class Roleplay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    async def _fetch(self, action: str) -> str | None:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        try:
            async with self.session.get(f"{NEKOS_BEST_BASE}/{action}") as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                results = data.get("results", [])
                return results[0]["url"] if results else None
        except aiohttp.ClientError:
            return None

    async def _run(self, ctx: commands.Context, action: str, target: discord.Member | None):
        url = await self._fetch(action)
        verb = VERBS[action]
        title = f"{ctx.author.display_name} {verb} {target.display_name}" if target else f"{ctx.author.display_name} {verb} the air"
        await ctx.send(view=embeds.image(title, url, emoji_key="cat_roleplay", fallback_text="Could not reach the image source right now — try again shortly."))

    @commands.hybrid_command(name="hug", description="Hug another member")
    async def hug(self, ctx: commands.Context, member: discord.Member = None):
        await self._run(ctx, "hug", member)

    @commands.hybrid_command(name="kiss", description="Kiss another member")
    async def kiss(self, ctx: commands.Context, member: discord.Member = None):
        await self._run(ctx, "kiss", member)

    @commands.hybrid_command(name="pat", description="Pat another member")
    async def pat(self, ctx: commands.Context, member: discord.Member = None):
        await self._run(ctx, "pat", member)

    @commands.hybrid_command(name="slap", description="Slap another member")
    async def slap(self, ctx: commands.Context, member: discord.Member = None):
        await self._run(ctx, "slap", member)

    @commands.hybrid_command(name="cuddle", description="Cuddle another member")
    async def cuddle(self, ctx: commands.Context, member: discord.Member = None):
        await self._run(ctx, "cuddle", member)

    @commands.hybrid_command(name="poke", description="Poke another member")
    async def poke(self, ctx: commands.Context, member: discord.Member = None):
        await self._run(ctx, "poke", member)

    @commands.hybrid_command(name="tickle", description="Tickle another member")
    async def tickle(self, ctx: commands.Context, member: discord.Member = None):
        await self._run(ctx, "tickle", member)

    @commands.hybrid_command(name="bite", description="Bite another member")
    async def bite(self, ctx: commands.Context, member: discord.Member = None):
        await self._run(ctx, "bite", member)

    @commands.hybrid_command(name="highfive", description="High-five another member")
    async def highfive(self, ctx: commands.Context, member: discord.Member = None):
        await self._run(ctx, "highfive", member)

    @commands.hybrid_command(name="wave", description="Wave at another member")
    async def wave(self, ctx: commands.Context, member: discord.Member = None):
        await self._run(ctx, "wave", member)

    async def cog_unload(self) -> None:
        if self.session:
            await self.session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(Roleplay(bot))
