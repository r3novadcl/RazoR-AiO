import base64
import binascii

from discord.ext import commands

from utils import embeds


class Conversion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="convert", description="Conversion utilities", invoke_without_command=True)
    async def convert(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @convert.command(name="dechex", description="Convert decimal to hexadecimal")
    async def dechex(self, ctx: commands.Context, number: int):
        await ctx.send(view=embeds.info("Decimal → Hex", f"`{number}` → `{hex(number)}`"), ephemeral=True)

    @convert.command(name="hexdec", description="Convert hexadecimal to decimal")
    async def hexdec(self, ctx: commands.Context, value: str):
        try:
            result = int(value, 16)
        except ValueError:
            await ctx.send(view=embeds.error("Invalid Hex"), ephemeral=True)
            return
        await ctx.send(view=embeds.info("Hex → Decimal", f"`{value}` → `{result}`"), ephemeral=True)

    @convert.command(name="binstr", description="Convert binary to text")
    async def binstr(self, ctx: commands.Context, *, binary: str):
        try:
            chars = binary.split()
            text = "".join(chr(int(b, 2)) for b in chars)
        except ValueError:
            await ctx.send(view=embeds.error("Invalid Binary", "Separate each byte with a space."), ephemeral=True)
            return
        await ctx.send(view=embeds.info("Binary → Text", text[:1900]), ephemeral=True)

    @convert.command(name="strbin", description="Convert text to binary")
    async def strbin(self, ctx: commands.Context, *, text: str):
        binary = " ".join(format(ord(c), "08b") for c in text)
        await ctx.send(view=embeds.info("Text → Binary", binary[:1900]), ephemeral=True)

    @convert.command(name="ft", description="Convert feet to metres")
    async def ft(self, ctx: commands.Context, feet: float):
        await ctx.send(view=embeds.info("Feet → Metres", f"`{feet}ft` → `{round(feet * 0.3048, 3)}m`"), ephemeral=True)

    @convert.command(name="kg", description="Convert kilograms to pounds")
    async def kg(self, ctx: commands.Context, kilograms: float):
        await ctx.send(view=embeds.info("Kg → Lb", f"`{kilograms}kg` → `{round(kilograms * 2.20462, 2)}lb`"), ephemeral=True)

    @convert.command(name="base64encode", description="Encode text as base64")
    async def base64encode(self, ctx: commands.Context, *, text: str):
        encoded = base64.b64encode(text.encode()).decode()
        await ctx.send(view=embeds.info("Base64 Encoded", encoded[:1900]), ephemeral=True)

    @convert.command(name="base64decode", description="Decode base64 text")
    async def base64decode(self, ctx: commands.Context, *, encoded: str):
        try:
            decoded = base64.b64decode(encoded).decode()
        except (binascii.Error, UnicodeDecodeError):
            await ctx.send(view=embeds.error("Invalid Base64"), ephemeral=True)
            return
        await ctx.send(view=embeds.info("Base64 Decoded", decoded[:1900]), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Conversion(bot))
