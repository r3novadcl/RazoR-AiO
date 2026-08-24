import io

import discord
from discord.ext import commands

from utils import database
from utils import embeds


class OwnerTools(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="setprefix", description="Change this server's command prefix")
    @commands.has_permissions(administrator=True)
    async def setprefix(self, ctx: commands.Context, new_prefix: str):
        if len(new_prefix) > 5:
            await ctx.send(view=embeds.error("Prefix Too Long", "Keep it under 5 characters."), ephemeral=True)
            return
        await database.set_guild_setting(ctx.guild.id, prefix=new_prefix)
        await ctx.send(view=embeds.success("Prefix Updated", f"New prefix: `{new_prefix}`"), ephemeral=True)

    @commands.hybrid_command(name="nick", description="Change a member's nickname")
    @commands.has_permissions(manage_nicknames=True)
    async def nick(self, ctx: commands.Context, member: discord.Member, *, nickname: str = None):
        try:
            await member.edit(nick=nickname, reason=f"Requested by {ctx.author}")
        except discord.Forbidden:
            await ctx.send(view=embeds.error("Cannot Edit Nickname", "That member outranks the bot."), ephemeral=True)
            return
        await ctx.send(view=embeds.success("Nickname Updated", f"{member.mention} → `{nickname or member.name}`"), ephemeral=True)

    async def _dump(self, ctx: commands.Context, filename: str, lines: list[str], label: str):
        if not lines:
            await ctx.send(view=embeds.info(f"Nothing to Dump", f"No {label} found."), ephemeral=True)
            return
        buffer = io.BytesIO("\n".join(lines).encode("utf-8"))
        await ctx.send(view=embeds.success(f"{label.capitalize()} Dump", f"{len(lines)} entries"),
                        file=discord.File(buffer, filename=filename))

    @commands.hybrid_group(name="dump", description="Export server data as a text file", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def dump(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @dump.command(name="channels", description="Export all channel names and IDs")
    @commands.has_permissions(administrator=True)
    async def dump_channels(self, ctx: commands.Context):
        lines = [f"{c.name} — {c.id} ({c.type})" for c in ctx.guild.channels]
        await self._dump(ctx, "channels.txt", lines, "channels")

    @dump.command(name="roles", description="Export all role names and IDs")
    @commands.has_permissions(administrator=True)
    async def dump_roles(self, ctx: commands.Context):
        lines = [f"{r.name} — {r.id} ({len(r.members)} members)" for r in ctx.guild.roles]
        await self._dump(ctx, "roles.txt", lines, "roles")

    @dump.command(name="bans", description="Export the ban list")
    @commands.has_permissions(ban_members=True)
    async def dump_bans(self, ctx: commands.Context):
        lines = [f"{entry.user} — {entry.user.id} — {entry.reason or 'No reason'}" async for entry in ctx.guild.bans()]
        await self._dump(ctx, "bans.txt", lines, "bans")

    @dump.command(name="emotes", description="Export all custom emoji names and IDs")
    @commands.has_permissions(administrator=True)
    async def dump_emotes(self, ctx: commands.Context):
        lines = [f"{e.name} — {e.id} — {e.url}" for e in ctx.guild.emojis]
        await self._dump(ctx, "emotes.txt", lines, "emotes")

    @dump.command(name="warns", description="Export all warnings issued in this server")
    @commands.has_permissions(administrator=True)
    async def dump_warns(self, ctx: commands.Context):
        cur = await database._conn().execute("SELECT * FROM warnings WHERE guild_id = ?", (ctx.guild.id,))
        rows = [dict(r) for r in await cur.fetchall()]
        lines = [f"#{r['id']} — user {r['user_id']} — mod {r['moderator_id']} — {r['reason']}" for r in rows]
        await self._dump(ctx, "warnings.txt", lines, "warnings")


async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerTools(bot))
