import discord
from discord.ext import commands

from utils import database
from utils import embeds


class AutoResponder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="autoresponder", description="Configure automatic trigger/response pairs", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def autoresponder(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @autoresponder.command(name="add", description="Add a trigger/response pair")
    @commands.has_permissions(administrator=True)
    async def autoresponder_add(self, ctx: commands.Context, exact_match: bool, trigger: str, *, response: str):
        responder_id = await database.add_autoresponder(ctx.guild.id, trigger, response, exact_match)
        await ctx.send(view=embeds.success("Autoresponder Added", f"`#{responder_id}` — `{trigger}` → {response[:100]}"), ephemeral=True)

    @autoresponder.command(name="remove", description="Remove an autoresponder by ID")
    @commands.has_permissions(administrator=True)
    async def autoresponder_remove(self, ctx: commands.Context, responder_id: int):
        await database.remove_autoresponder(ctx.guild.id, responder_id)
        await ctx.send(view=embeds.success("Autoresponder Removed", f"`#{responder_id}`"), ephemeral=True)

    @autoresponder.command(name="list", description="List all autoresponders")
    async def autoresponder_list(self, ctx: commands.Context):
        rows = await database.get_autoresponders(ctx.guild.id)
        if not rows:
            await ctx.send(view=embeds.info("No Autoresponders", "None configured yet."), ephemeral=True)
            return
        lines = [f"`#{r['id']}` — `{r['trigger']}` ({'exact' if r['exact_match'] else 'contains'})" for r in rows]
        await ctx.send(view=embeds.SectionLayout("Autoresponders", lines), ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        rows = await database.get_autoresponders(message.guild.id)
        content = message.content.lower()
        for row in rows:
            trigger = row["trigger"].lower()
            matched = content == trigger if row["exact_match"] else trigger in content
            if matched:
                try:
                    await message.channel.send(row["response"])
                except discord.HTTPException:
                    pass
                return


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoResponder(bot))
