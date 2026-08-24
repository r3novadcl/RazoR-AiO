import discord
from discord.ext import commands

from utils import database
from utils import embeds


class AutoReact(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="autoreact", description="Auto-react to messages containing a trigger word", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def autoreact(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @autoreact.command(name="add", description="Add a trigger word -> emoji pair")
    @commands.has_permissions(administrator=True)
    async def autoreact_add(self, ctx: commands.Context, trigger: str, emoji: str):
        entry_id = await database.add_autoreact(ctx.guild.id, trigger.lower(), emoji)
        await ctx.send(view=embeds.success("Autoreact Added", f"`#{entry_id}` `{trigger}` → {emoji}"), ephemeral=True)

    @autoreact.command(name="remove", description="Remove an autoreact by ID")
    @commands.has_permissions(administrator=True)
    async def autoreact_remove(self, ctx: commands.Context, entry_id: int):
        await database.remove_autoreact(ctx.guild.id, entry_id)
        await ctx.send(view=embeds.success("Autoreact Removed", f"`#{entry_id}`"), ephemeral=True)

    @autoreact.command(name="list", description="List all autoreacts")
    async def autoreact_list(self, ctx: commands.Context):
        rows = await database.get_autoreacts(ctx.guild.id)
        if not rows:
            await ctx.send(view=embeds.info("No Autoreacts"), ephemeral=True)
            return
        lines = [f"`#{r['id']}` `{r['trigger']}` → {r['emoji']}" for r in rows]
        await ctx.send(view=embeds.SectionLayout("Autoreacts", lines), ephemeral=True)

    @autoreact.command(name="reset", description="Remove all autoreacts")
    @commands.has_permissions(administrator=True)
    async def autoreact_reset(self, ctx: commands.Context):
        await database.clear_autoreacts(ctx.guild.id)
        await ctx.send(view=embeds.success("Autoreacts Cleared"), ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        rows = await database.get_autoreacts(message.guild.id)
        content = message.content.lower()
        for row in rows:
            if row["trigger"] in content:
                try:
                    await message.add_reaction(row["emoji"])
                except discord.HTTPException:
                    pass


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoReact(bot))
