import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils import database
from utils import embeds

log = logging.getLogger("RazoR")


def is_owner_or_extraowner():
    async def predicate(ctx: commands.Context) -> bool:
        guild = ctx.guild
        if guild is None:
            return False
        if ctx.author.id == guild.owner_id:
            return True
        if guild.id not in database._antinuke_cache:
            await database.refresh_antinuke(guild.id)
        cfg = database.get_antinuke_config(guild.id)
        if ctx.author.id in cfg["extraowners"]:
            return True
        raise commands.CheckFailure(
            "Only the server owner or an added extraowner can use this — Administrator permission is not enough by design."
        )

    return commands.check(predicate)


async def handle_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, (commands.CheckFailure, app_commands.CheckFailure)):
        await ctx.send(view=embeds.error("Access Denied", str(error)), ephemeral=True)
        return
    if isinstance(error, commands.MissingPermissions):
        missing = ", ".join(error.missing_permissions)
        await ctx.send(view=embeds.error("Missing Permissions", f"You need: `{missing}`"), ephemeral=True)
        return
    if isinstance(error, commands.BotMissingPermissions):
        missing = ", ".join(error.missing_permissions)
        await ctx.send(view=embeds.error("I'm Missing Permissions", f"I need: `{missing}`"), ephemeral=True)
        return
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(view=embeds.warning("On Cooldown", f"Try again in `{error.retry_after:.1f}s`."), ephemeral=True)
        return
    if isinstance(error, commands.MemberNotFound):
        await ctx.send(view=embeds.error("Member Not Found", str(error)), ephemeral=True)
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(view=embeds.error("Missing Argument", f"`{error.param.name}` is required."), ephemeral=True)
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send(view=embeds.error("Invalid Argument", str(error)), ephemeral=True)
        return
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send(view=embeds.error("Server Only", "This command only works inside a server."), ephemeral=True)
        return
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CommandInvokeError):
        log.error(f"Unhandled error in command '{ctx.command}'", exc_info=error.original)
        await ctx.send(view=embeds.error("Something Went Wrong", "That command hit an unexpected error — it's been logged."), ephemeral=True)
        return
    raise error


async def handle_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.CheckFailure):
        view = embeds.error("Access Denied", str(error))
    elif isinstance(error, app_commands.CommandOnCooldown):
        view = embeds.warning("On Cooldown", f"Try again in `{error.retry_after:.1f}s`.")
    elif isinstance(error, app_commands.MissingPermissions):
        view = embeds.error("Missing Permissions", f"You need: `{', '.join(error.missing_permissions)}`")
    elif isinstance(error, app_commands.BotMissingPermissions):
        view = embeds.error("I'm Missing Permissions", f"I need: `{', '.join(error.missing_permissions)}`")
    elif isinstance(error, app_commands.CommandInvokeError):
        name = interaction.command.qualified_name if interaction.command else "?"
        log.error(f"Unhandled error in app command '{name}'", exc_info=error.original)
        view = embeds.error("Something Went Wrong", "That command hit an unexpected error — it's been logged.")
    else:
        log.error("Unhandled app command error", exc_info=error)
        view = embeds.error("Something Went Wrong", "That command hit an unexpected error — it's been logged.")

    if interaction.response.is_done():
        await interaction.followup.send(view=view, ephemeral=True)
    else:
        await interaction.response.send_message(view=view, ephemeral=True)
