import discord
from discord.ext import commands

import config
from utils import embeds

try:
    import wavelink
    WAVELINK_AVAILABLE = True
except ImportError:
    WAVELINK_AVAILABLE = False


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.node_ready = False

    async def cog_load(self) -> None:
        if not WAVELINK_AVAILABLE or not config.LAVALINK_HOST:
            return
        try:
            node = wavelink.Node(
                uri=f"{'https' if config.LAVALINK_SECURE else 'http'}://{config.LAVALINK_HOST}:{config.LAVALINK_PORT}",
                password=config.LAVALINK_PASSWORD,
            )
            await wavelink.Pool.connect(nodes=[node], client=self.bot)
            self.node_ready = True
        except Exception:
            self.node_ready = False

    def _not_configured(self) -> discord.ui.LayoutView:
        return embeds.warning(
            "Music Not Configured",
            "This bot needs a Lavalink server. Set `LAVALINK_HOST`, `LAVALINK_PORT`, and `LAVALINK_PASSWORD` in `.env` to enable music.",
        )

    @commands.hybrid_command(name="play", description="Play a song")
    async def play(self, ctx: commands.Context, *, query: str):
        if not self.node_ready:
            await ctx.send(view=self._not_configured(), ephemeral=True)
            return
        if ctx.author.voice is None:
            await ctx.send(view=embeds.error("Join a Voice Channel First"), ephemeral=True)
            return

        player: wavelink.Player = ctx.voice_client or await ctx.author.voice.channel.connect(cls=wavelink.Player)
        tracks = await wavelink.Playable.search(query)
        if not tracks:
            await ctx.send(view=embeds.error("No Results", query), ephemeral=True)
            return

        track = tracks[0]
        if player.playing:
            await player.queue.put_wait(track)
            await ctx.send(view=embeds.success("Queued", track.title))
        else:
            await player.play(track)
            await ctx.send(view=embeds.success("Now Playing", track.title))

    @commands.hybrid_command(name="skip", description="Skip the current song")
    async def skip(self, ctx: commands.Context):
        if not self.node_ready:
            await ctx.send(view=self._not_configured(), ephemeral=True)
            return
        player: wavelink.Player = ctx.voice_client
        if player is None:
            await ctx.send(view=embeds.error("Nothing Playing"), ephemeral=True)
            return
        await player.skip()
        await ctx.send(view=embeds.success("Skipped"))

    @commands.hybrid_command(name="stop", description="Stop playback and disconnect")
    async def stop(self, ctx: commands.Context):
        if not self.node_ready:
            await ctx.send(view=self._not_configured(), ephemeral=True)
            return
        player: wavelink.Player = ctx.voice_client
        if player is None:
            await ctx.send(view=embeds.error("Nothing Playing"), ephemeral=True)
            return
        await player.disconnect()
        await ctx.send(view=embeds.success("Stopped"))

    @commands.hybrid_command(name="queue", description="Show the music queue")
    async def queue(self, ctx: commands.Context):
        if not self.node_ready:
            await ctx.send(view=self._not_configured(), ephemeral=True)
            return
        player: wavelink.Player = ctx.voice_client
        if player is None or not player.queue:
            await ctx.send(view=embeds.info("Queue Empty"), ephemeral=True)
            return
        lines = [f"{i+1}. {t.title}" for i, t in enumerate(player.queue)]
        await ctx.send(view=embeds.SectionLayout("Queue", lines))


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
