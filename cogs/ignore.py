import discord
from discord.ext import commands

from utils import database
from utils import embeds


class Ignore(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="ignore", description="Exclude channels/users from automod and leveling", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def ignore(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @ignore.group(name="channel", description="Ignore a channel", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def ignore_channel(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @ignore_channel.command(name="add")
    @commands.has_permissions(administrator=True)
    async def ignore_channel_add(self, ctx: commands.Context, channel: discord.TextChannel):
        await database.add_ignore(ctx.guild.id, "ignore_channels", "channel_id", channel.id)
        await ctx.send(view=embeds.success("Channel Ignored", channel.mention), ephemeral=True)

    @ignore_channel.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def ignore_channel_remove(self, ctx: commands.Context, channel: discord.TextChannel):
        await database.remove_ignore(ctx.guild.id, "ignore_channels", "channel_id", channel.id)
        await ctx.send(view=embeds.success("Channel Unignored", channel.mention), ephemeral=True)

    @ignore_channel.command(name="show")
    async def ignore_channel_show(self, ctx: commands.Context):
        ids = await database.get_ignored(ctx.guild.id, "ignore_channels", "channel_id")
        lines = [f"<#{i}>" for i in ids] or ["None"]
        await ctx.send(view=embeds.SectionLayout("Ignored Channels", lines), ephemeral=True)

    @ignore.group(name="user", description="Ignore a user", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def ignore_user(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @ignore_user.command(name="add")
    @commands.has_permissions(administrator=True)
    async def ignore_user_add(self, ctx: commands.Context, member: discord.Member):
        await database.add_ignore(ctx.guild.id, "ignore_users", "user_id", member.id)
        await ctx.send(view=embeds.success("User Ignored", member.mention), ephemeral=True)

    @ignore_user.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def ignore_user_remove(self, ctx: commands.Context, member: discord.Member):
        await database.remove_ignore(ctx.guild.id, "ignore_users", "user_id", member.id)
        await ctx.send(view=embeds.success("User Unignored", member.mention), ephemeral=True)

    @ignore_user.command(name="show")
    async def ignore_user_show(self, ctx: commands.Context):
        ids = await database.get_ignored(ctx.guild.id, "ignore_users", "user_id")
        lines = [f"<@{i}>" for i in ids] or ["None"]
        await ctx.send(view=embeds.SectionLayout("Ignored Users", lines), ephemeral=True)


async def is_ignored(guild_id: int, user_id: int, channel_id: int) -> bool:
    users = await database.get_ignored(guild_id, "ignore_users", "user_id")
    if user_id in users:
        return True
    channels = await database.get_ignored(guild_id, "ignore_channels", "channel_id")
    return channel_id in channels


async def setup(bot: commands.Bot):
    await bot.add_cog(Ignore(bot))
