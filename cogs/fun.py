import random

import discord
from discord.ext import commands

from utils import embeds
from utils import emojis

EIGHT_BALL_ANSWERS = [
    "It is certain.", "Without a doubt.", "Yes, definitely.", "You may rely on it.",
    "As I see it, yes.", "Most likely.", "Outlook good.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
    "Cannot predict now.", "Don't count on it.", "My reply is no.",
    "Outlook not so good.", "Very doubtful.",
]

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "Why did the developer go broke? Because they used up all their cache.",
    "There are 10 types of people: those who understand binary and those who don't.",
    "Why do Java developers wear glasses? Because they don't C#.",
    "A SQL query walks into a bar, walks up to two tables and asks: can I join you?",
]


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="8ball", description="Ask the magic 8-ball a question")
    async def eight_ball(self, ctx: commands.Context, *, question: str):
        await ctx.send(view=embeds.info(f"{emojis.get('eightball', '🎱')} {question}", random.choice(EIGHT_BALL_ANSWERS)))

    @commands.hybrid_command(name="coinflip", description="Flip a coin")
    async def coinflip(self, ctx: commands.Context):
        await ctx.send(view=embeds.info("Coin Flip", random.choice(["Heads!", "Tails!"])))

    @commands.hybrid_command(name="dice", description="Roll a dice")
    async def dice(self, ctx: commands.Context, sides: int = 6):
        if sides < 2:
            sides = 6
        await ctx.send(view=embeds.info("Dice Roll", f"{emojis.get('dice', '🎲')} You rolled a **{random.randint(1, sides)}** (d{sides})"))

    @commands.hybrid_command(name="ship", description="Ship two members")
    async def ship(self, ctx: commands.Context, first: discord.Member, second: discord.Member):
        score = random.randint(0, 100)
        await ctx.send(view=embeds.info(f"{emojis.get('heart', '💘')} {first.display_name} x {second.display_name}", f"Compatibility: **{score}%**"))

    @commands.hybrid_command(name="joke", description="Get a random joke")
    async def joke(self, ctx: commands.Context):
        await ctx.send(view=embeds.info(f"{emojis.get('laugh', '😂')} Joke", random.choice(JOKES)))

    @commands.hybrid_command(name="rate", description="Rate anything out of 10")
    async def rate(self, ctx: commands.Context, *, thing: str):
        await ctx.send(view=embeds.info(f"Rating: {thing}", f"I'd give it a **{random.randint(0, 10)}/10**"))

    @commands.hybrid_command(name="texttoemoji", description="Convert text to regional indicator emojis")
    async def texttoemoji(self, ctx: commands.Context, *, text: str):
        result = []
        for char in text.lower():
            if char.isalpha():
                result.append(f":regional_indicator_{char}:")
            elif char == " ":
                result.append("   ")
            else:
                result.append(char)
        await ctx.send(view=embeds.info("Text to Emoji", " ".join(result)[:1900]))


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
