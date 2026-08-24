from discord.ext import commands

from utils import database
from utils import embeds


class Todo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="todo", description="Your personal to-do list", invoke_without_command=True)
    async def todo(self, ctx: commands.Context):
        await self.todo_list(ctx)

    @todo.command(name="add", description="Add an item to your to-do list")
    async def todo_add(self, ctx: commands.Context, *, item: str):
        todo_id = await database.add_todo(ctx.author.id, item)
        await ctx.send(view=embeds.success("Added", f"`#{todo_id}` {item}"), ephemeral=True)

    @todo.command(name="remove", description="Remove an item from your to-do list")
    async def todo_remove(self, ctx: commands.Context, item_id: int):
        await database.remove_todo(ctx.author.id, item_id)
        await ctx.send(view=embeds.success("Removed", f"`#{item_id}`"), ephemeral=True)

    @todo.command(name="list", description="Show your to-do list")
    async def todo_list(self, ctx: commands.Context):
        items = await database.get_todos(ctx.author.id)
        if not items:
            await ctx.send(view=embeds.info("Empty List", "Nothing on your to-do list yet."), ephemeral=True)
            return
        lines = [f"`#{i['id']}` {i['content']}" for i in items]
        await ctx.send(view=embeds.SectionLayout(f"{ctx.author.display_name}'s To-Do List", lines), ephemeral=True)

    @todo.command(name="clear", description="Clear your entire to-do list")
    async def todo_clear(self, ctx: commands.Context):
        await database.clear_todos(ctx.author.id)
        await ctx.send(view=embeds.success("Cleared"), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Todo(bot))
