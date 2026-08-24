import io

import discord
from discord.ext import commands

import config
from utils import embeds


class Steal(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="steal", description="Add an emoji from another server into this one")
    @commands.has_permissions(manage_emojis=True)
    async def steal(self, ctx: commands.Context, emoji: discord.PartialEmoji, *, new_name: str = None):
        try:
            image_bytes = await emoji.read()
        except discord.HTTPException:
            await ctx.send(view=embeds.error("Could Not Fetch Emoji"), ephemeral=True)
            return

        try:
            created = await ctx.guild.create_custom_emoji(name=new_name or emoji.name, image=image_bytes)
        except discord.HTTPException as exc:
            await ctx.send(view=embeds.error("Failed to Add Emoji", str(exc)), ephemeral=True)
            return

        await ctx.send(view=embeds.success("Emoji Added", f"{created} `:{created.name}:`"))

    @commands.hybrid_command(name="stealsticker", description="Add a sticker from a message into this server")
    @commands.has_permissions(manage_emojis=True)
    async def stealsticker(self, ctx: commands.Context, message_id: str):
        try:
            message = await ctx.channel.fetch_message(int(message_id))
        except discord.NotFound:
            await ctx.send(view=embeds.error("Message Not Found"), ephemeral=True)
            return

        if not message.stickers:
            await ctx.send(view=embeds.error("No Sticker Found", "That message has no stickers."), ephemeral=True)
            return

        sticker = message.stickers[0]
        try:
            image_bytes = await sticker.read()
            file = discord.File(io.BytesIO(image_bytes), filename=f"{sticker.name}.png")
            created = await ctx.guild.create_sticker(
                name=sticker.name, description=sticker.name, emoji=config.DEFAULT_STICKER_EMOJI, file=file,
                reason=f"Stolen by {ctx.author}",
            )
        except discord.HTTPException as exc:
            await ctx.send(view=embeds.error("Failed to Add Sticker", str(exc)), ephemeral=True)
            return

        await ctx.send(view=embeds.success("Sticker Added", created.name))


async def setup(bot: commands.Bot):
    await bot.add_cog(Steal(bot))
