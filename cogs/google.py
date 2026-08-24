import aiohttp
from discord.ext import commands

import config
from utils import embeds


class Google(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    @commands.hybrid_command(name="google", description="Search Google")
    async def google(self, ctx: commands.Context, *, query: str):
        if not (config.GOOGLE_API_KEY and config.GOOGLE_CSE_ID):
            await ctx.send(view=embeds.warning("Google Search Not Configured", "Set `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` in `.env` to enable this."), ephemeral=True)
            return

        if self.session is None:
            self.session = aiohttp.ClientSession()

        params = {"key": config.GOOGLE_API_KEY, "cx": config.GOOGLE_CSE_ID, "q": query}
        try:
            async with self.session.get("https://www.googleapis.com/customsearch/v1", params=params) as resp:
                if resp.status != 200:
                    await ctx.send(view=embeds.error("Search Failed", f"Status {resp.status}"), ephemeral=True)
                    return
                data = await resp.json()
        except aiohttp.ClientError:
            await ctx.send(view=embeds.error("Search Failed", "Could not reach Google right now."), ephemeral=True)
            return

        items = data.get("items", [])[:5]
        if not items:
            await ctx.send(view=embeds.info("No Results", query), ephemeral=True)
            return

        lines = [f"**[{i['title']}]({i['link']})**\n{i.get('snippet', '')}" for i in items]
        await ctx.send(view=embeds.SectionLayout(f"Google: {query}", lines))

    async def cog_unload(self) -> None:
        if self.session:
            await self.session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(Google(bot))
