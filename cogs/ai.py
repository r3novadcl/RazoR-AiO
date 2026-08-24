import aiohttp
import discord
from discord.ext import commands

import config
from utils import embeds
from utils import emojis


class AI(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    def _configured(self) -> bool:
        return bool(config.AI_API_KEY)

    @commands.hybrid_group(name="ai", description="AI-powered chat", invoke_without_command=True)
    async def ai(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @ai.command(name="ask", description="Ask the AI a question")
    async def ask(self, ctx: commands.Context, *, question: str):
        if not self._configured():
            await ctx.send(view=embeds.warning("AI Not Configured", "Set `AI_API_KEY` in `.env` to enable this."), ephemeral=True)
            return

        await ctx.defer()
        if self.session is None:
            self.session = aiohttp.ClientSession()

        headers = {"Authorization": f"Bearer {config.AI_API_KEY}"}
        payload = {"model": config.AI_MODEL, "messages": [{"role": "user", "content": question}]}
        try:
            async with self.session.post(f"{config.AI_API_BASE}/chat/completions", json=payload, headers=headers) as resp:
                if resp.status != 200:
                    await ctx.send(view=embeds.error("AI Request Failed", f"Status {resp.status}"), ephemeral=True)
                    return
                data = await resp.json()
                answer = data["choices"][0]["message"]["content"]
        except (aiohttp.ClientError, KeyError, IndexError):
            await ctx.send(view=embeds.error("AI Request Failed", "Could not reach the configured AI endpoint."), ephemeral=True)
            return

        await ctx.send(view=embeds.info(f"{emojis.get('robot', '🤖')} {question[:100]}", answer[:1900]))

    async def cog_unload(self) -> None:
        if self.session:
            await self.session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(AI(bot))
