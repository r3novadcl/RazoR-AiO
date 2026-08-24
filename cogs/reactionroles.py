import discord
from discord.ext import commands

import config
from utils import database
from utils import embeds
from utils import emojis


class ReactionRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="reactionrole", description="Bind emoji reactions on a message to roles", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def reactionrole(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @reactionrole.command(name="add", description="Bind an emoji reaction on a message to a role")
    @commands.has_permissions(administrator=True)
    async def reactionrole_add(self, ctx: commands.Context, message_id: str, emoji: str, role: discord.Role):
        channel = ctx.channel
        try:
            message = await channel.fetch_message(int(message_id))
        except (discord.NotFound, ValueError):
            await ctx.send(view=embeds.error("Message Not Found", "Make sure you're in the same channel as the message."), ephemeral=True)
            return

        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            await ctx.send(view=embeds.error("Invalid Emoji", "The bot couldn't react with that emoji."), ephemeral=True)
            return

        await database.add_reaction_role(ctx.guild.id, channel.id, message.id, emoji, role.id)
        await ctx.send(view=embeds.success("Reaction Role Added", f"{emoji} → {role.mention}"), ephemeral=True)

    @reactionrole.command(name="list", description="List all reaction roles in this server")
    async def reactionrole_list(self, ctx: commands.Context):
        rows = await database.get_guild_reaction_roles(ctx.guild.id)
        if not rows:
            await ctx.send(view=embeds.info("No Reaction Roles"), ephemeral=True)
            return
        lines = [f"`#{r['id']}` {r['emoji']} → <@&{r['role_id']}> (message `{r['message_id']}`)" for r in rows]
        await ctx.send(view=embeds.SectionLayout(f"{emojis.get('cat_reactionroles', '🎭')} Reaction Roles", lines), ephemeral=True)

    @reactionrole.command(name="remove", description="Remove a reaction role by its ID")
    @commands.has_permissions(administrator=True)
    async def reactionrole_remove(self, ctx: commands.Context, entry_id: int):
        await database.remove_reaction_role(ctx.guild.id, entry_id)
        await ctx.send(view=embeds.success("Reaction Role Removed", f"`#{entry_id}`"), ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member is None or payload.member.bot:
            return
        binding = await database.get_reaction_role(payload.message_id, str(payload.emoji))
        if binding is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        role = guild.get_role(binding["role_id"]) if guild else None
        if guild and role:
            try:
                await payload.member.add_roles(role, reason="Reaction role")
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        binding = await database.get_reaction_role(payload.message_id, str(payload.emoji))
        if binding is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        role = guild.get_role(binding["role_id"])
        if member and role:
            try:
                await member.remove_roles(role, reason="Reaction role removed")
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRoles(bot))
