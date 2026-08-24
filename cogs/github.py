import aiohttp
from discord.ext import commands

from utils import embeds

API_BASE = "https://api.github.com"


class GitHub(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    @commands.hybrid_command(name="github", description="Look up a public GitHub repository")
    async def github(self, ctx: commands.Context, owner_repo: str):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        try:
            async with self.session.get(f"{API_BASE}/repos/{owner_repo}") as resp:
                if resp.status != 200:
                    await ctx.send(view=embeds.error("Not Found", f"Could not find `{owner_repo}`."), ephemeral=True)
                    return
                data = await resp.json()
        except aiohttp.ClientError:
            await ctx.send(view=embeds.error("Request Failed", "Could not reach GitHub right now."), ephemeral=True)
            return

        view = embeds.SectionLayout(
            data.get("full_name", owner_repo),
            [
                data.get("description") or "No description.",
                f"Stars: {data.get('stargazers_count', 0)} • Forks: {data.get('forks_count', 0)} • Open issues: {data.get('open_issues_count', 0)}\n"
                f"**Language:** {data.get('language') or 'Unknown'}\n{data.get('html_url', '')}",
            ],
        )
        await ctx.send(view=view)

    async def cog_unload(self) -> None:
        if self.session:
            await self.session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(GitHub(bot))
