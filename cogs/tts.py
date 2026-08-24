import io

import discord
from discord.ext import commands

from utils import embeds

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


class TTS(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="tts", description="Convert text to a speech audio file")
    async def tts(self, ctx: commands.Context, *, text: str):
        if not GTTS_AVAILABLE:
            await ctx.send(view=embeds.warning("TTS Not Available", "Install `gTTS` (uncomment it in requirements.txt) to enable this."), ephemeral=True)
            return
        if len(text) > 500:
            await ctx.send(view=embeds.error("Text Too Long", "Keep it under 500 characters."), ephemeral=True)
            return

        await ctx.defer()
        buffer = io.BytesIO()
        gTTS(text=text).write_to_fp(buffer)
        buffer.seek(0)
        await ctx.send(view=embeds.success("Text-to-Speech", text[:200]), file=discord.File(buffer, filename="tts.mp3"))


async def setup(bot: commands.Bot):
    await bot.add_cog(TTS(bot))
