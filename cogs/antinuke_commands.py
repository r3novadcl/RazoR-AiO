import discord
from discord import app_commands
from discord.ext import commands

import config
from utils import database
from utils import embeds
from utils import emojis
from utils.checks import is_owner_or_extraowner


async def run_setup(guild: discord.Guild, log_channel: discord.TextChannel) -> None:
    no_bypass = discord.utils.get(guild.roles, name=config.ANTINUKE_NO_BYPASS_ROLE)
    if no_bypass is None:
        no_bypass = await guild.create_role(name=config.ANTINUKE_NO_BYPASS_ROLE, colour=discord.Colour.red())

    barrier = discord.utils.get(guild.roles, name=config.ANTINUKE_BARRIER_ROLE)
    if barrier is None:
        barrier = await guild.create_role(name=config.ANTINUKE_BARRIER_ROLE, colour=discord.Colour.greyple())

    await database.save_antinuke_core(
        guild.id,
        enabled=True,
        setup_done=True,
        punishment=config.ANTINUKE_DEFAULT_PUNISHMENT,
        log_channel=log_channel.id,
        no_bypass_role_id=no_bypass.id,
        barrier_role_id=barrier.id,
        events=dict(database.DEFAULT_EVENTS),
    )


class IntroView(discord.ui.LayoutView):
    def __init__(self, guild_id: int):
        super().__init__(timeout=120)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(
            f"{emojis.get('shield', '🛡️')} **What is Anti-Nuke?**\n\n"
            "Anti-Nuke watches every dangerous server action — channel/role deletion, mass bans, "
            "permission escalation, webhook abuse, and more — resolves who did it via the audit log, "
            "and automatically strips/kicks/bans anyone who isn't the owner, an extraowner, or on your trusted lists.\n\n"
            "It creates two roles (`No-Bypass`, `Barrier ~ Unit`) and needs a log channel for alerts."
        ))
        row = discord.ui.ActionRow()
        row.add_item(ProceedButton(guild_id))
        row.add_item(StopButton())
        container.add_item(row)
        self.add_item(container)


class ProceedButton(discord.ui.Button):
    def __init__(self, guild_id: int):
        super().__init__(label="Proceed", style=discord.ButtonStyle.success)
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=LimitationsView(self.guild_id))


class StopButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Stop", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=embeds.info("Setup Cancelled"))


class LimitationsView(discord.ui.LayoutView):
    def __init__(self, guild_id: int):
        super().__init__(timeout=120)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR_WARN)
        container.add_item(discord.ui.TextDisplay(
            f"{emojis.get('warning', '⚠️')} **Limitations, please read**\n\n"
            "- The bot's role must sit above anyone it needs to punish.\n"
            "- It can only act on events Discord's audit log actually records, within a short lookback window.\n"
            "- Server owners and Administrators are not automatically immune unless added as an extraowner/whitelist — "
            "this is intentional, since Administrator alone is the most common real bypass.\n"
            "- Punishment mode defaults to role-strip; review `/antinuke punishment` if you'd rather kick/ban."
        ))
        row = discord.ui.ActionRow()
        row.add_item(AgreeButton(guild_id))
        row.add_item(DisagreeButton())
        container.add_item(row)
        self.add_item(container)


class AgreeButton(discord.ui.Button):
    def __init__(self, guild_id: int):
        super().__init__(label="Agree & Continue", style=discord.ButtonStyle.success)
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=LogChannelView(self.guild_id))


class DisagreeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Don't Agree", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=embeds.info("Setup Cancelled"))


class LogChannelView(discord.ui.LayoutView):
    def __init__(self, guild_id: int):
        super().__init__(timeout=120)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(f"{emojis.get('book', '📋')} **Final step** — choose the channel anti-nuke alerts should be logged to."))
        row = discord.ui.ActionRow()
        row.add_item(LogChannelSelect(guild_id))
        container.add_item(row)
        self.add_item(container)


class LogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, guild_id: int):
        super().__init__(placeholder="Choose the log channel", channel_types=[discord.ChannelType.text])
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        channel = self.values[0]
        await run_setup(guild, channel)
        await interaction.edit_original_response(
            view=embeds.success(
                "Anti-Nuke Configured",
                f"Protection is now **enabled**.\nLog channel: {channel.mention}\n"
                f"Default punishment: `{config.ANTINUKE_DEFAULT_PUNISHMENT}`\n"
                "Use `/antinuke status` any time to review the full configuration.",
            )
        )


class AntiNuke(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="antinuke", description="Configure server anti-nuke protection", invoke_without_command=True)
    async def antinuke(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @antinuke.command(name="setup", description="Open the guided anti-nuke setup wizard")
    @is_owner_or_extraowner()
    async def antinuke_setup(self, ctx: commands.Context):
        await ctx.send(view=IntroView(ctx.guild.id), ephemeral=True)

    @antinuke.command(name="enable", description="Enable anti-nuke protection")
    @is_owner_or_extraowner()
    async def antinuke_enable(self, ctx: commands.Context):
        await database.save_antinuke_core(ctx.guild.id, enabled=True)
        await ctx.send(view=embeds.success("Anti-Nuke Enabled"), ephemeral=True)

    @antinuke.command(name="disable", description="Disable anti-nuke protection")
    @is_owner_or_extraowner()
    async def antinuke_disable(self, ctx: commands.Context):
        await database.save_antinuke_core(ctx.guild.id, enabled=False)
        await ctx.send(view=embeds.warning("Anti-Nuke Disabled"), ephemeral=True)

    @antinuke.command(name="punishment", description="Set what happens to a caught attacker")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Strip Roles", value="strip"),
        app_commands.Choice(name="Kick", value="kick"),
        app_commands.Choice(name="Ban", value="ban"),
    ])
    @is_owner_or_extraowner()
    async def antinuke_punishment(self, ctx: commands.Context, mode: str):
        if mode not in ("strip", "kick", "ban"):
            await ctx.send(view=embeds.error("Invalid Mode", "Choose one of: `strip`, `kick`, `ban`"), ephemeral=True)
            return
        await database.save_antinuke_core(ctx.guild.id, punishment=mode)
        await ctx.send(view=embeds.success("Punishment Updated", f"Attackers will now be **{mode}**."), ephemeral=True)

    @antinuke.command(name="logchannel", description="Set the anti-nuke alert log channel")
    @is_owner_or_extraowner()
    async def antinuke_logchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        await database.save_antinuke_core(ctx.guild.id, log_channel=channel.id)
        await ctx.send(view=embeds.success("Log Channel Updated", f"Alerts will be sent to {channel.mention}."), ephemeral=True)

    @antinuke.command(name="toggle", description="Turn a specific protection type on or off")
    @app_commands.choices(event=[app_commands.Choice(name=config.ANTINUKE_EVENT_LABELS[k], value=k) for k in config.ANTINUKE_EVENT_KEYS])
    @is_owner_or_extraowner()
    async def antinuke_toggle(self, ctx: commands.Context, event: str, state: bool):
        if event not in config.ANTINUKE_EVENT_KEYS:
            await ctx.send(view=embeds.error("Invalid Event", f"Must be one of: {', '.join(config.ANTINUKE_EVENT_KEYS)}"), ephemeral=True)
            return
        if ctx.guild.id not in database._antinuke_cache:
            await database.refresh_antinuke(ctx.guild.id)
        cfg = database.get_antinuke_config(ctx.guild.id)
        cfg["events"][event] = state
        await database.save_antinuke_core(ctx.guild.id, events=cfg["events"])
        label = config.ANTINUKE_EVENT_LABELS[event]
        await ctx.send(view=embeds.success("Protection Updated", f"**{label}** is now **{'ON' if state else 'OFF'}**."), ephemeral=True)

    @antinuke.group(name="whitelist", description="Members immune to antinuke punishment", invoke_without_command=True)
    async def antinuke_whitelist(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @antinuke_whitelist.command(name="add")
    @is_owner_or_extraowner()
    async def whitelist_add(self, ctx: commands.Context, user: discord.Member):
        await database.antinuke_list_add(ctx.guild.id, "antinuke_whitelist", "user_id", user.id)
        await ctx.send(view=embeds.success("Whitelisted", f"{user.mention} is now immune."), ephemeral=True)

    @antinuke_whitelist.command(name="remove")
    @is_owner_or_extraowner()
    async def whitelist_remove(self, ctx: commands.Context, user: discord.Member):
        await database.antinuke_list_remove(ctx.guild.id, "antinuke_whitelist", "user_id", user.id)
        await ctx.send(view=embeds.success("Removed", f"{user.mention} removed from whitelist."), ephemeral=True)

    @antinuke.group(name="extraowner", description="Additional trusted owners", invoke_without_command=True)
    async def antinuke_extraowner(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @antinuke_extraowner.command(name="add")
    @is_owner_or_extraowner()
    async def extraowner_add(self, ctx: commands.Context, user: discord.Member):
        await database.antinuke_list_add(ctx.guild.id, "antinuke_extraowners", "user_id", user.id)
        await ctx.send(view=embeds.success("Extraowner Added", user.mention), ephemeral=True)

    @antinuke_extraowner.command(name="remove")
    @is_owner_or_extraowner()
    async def extraowner_remove(self, ctx: commands.Context, user: discord.Member):
        await database.antinuke_list_remove(ctx.guild.id, "antinuke_extraowners", "user_id", user.id)
        await ctx.send(view=embeds.success("Extraowner Removed", user.mention), ephemeral=True)

    @antinuke.group(name="mainrole", description="Roles treated as trusted staff", invoke_without_command=True)
    async def antinuke_mainrole(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @antinuke_mainrole.command(name="add")
    @is_owner_or_extraowner()
    async def mainrole_add(self, ctx: commands.Context, role: discord.Role):
        await database.antinuke_list_add(ctx.guild.id, "antinuke_mainroles", "role_id", role.id)
        await ctx.send(view=embeds.success("Mainrole Added", role.mention), ephemeral=True)

    @antinuke_mainrole.command(name="remove")
    @is_owner_or_extraowner()
    async def mainrole_remove(self, ctx: commands.Context, role: discord.Role):
        await database.antinuke_list_remove(ctx.guild.id, "antinuke_mainroles", "role_id", role.id)
        await ctx.send(view=embeds.success("Mainrole Removed", role.mention), ephemeral=True)

    @antinuke.command(name="status", description="View the full anti-nuke configuration")
    async def antinuke_status(self, ctx: commands.Context):
        if ctx.guild.id not in database._antinuke_cache:
            await database.refresh_antinuke(ctx.guild.id)
        cfg = database.get_antinuke_config(ctx.guild.id)
        stats = await database.get_antinuke_stats(ctx.guild.id)

        events_block = "\n".join(
            f"{emojis.get('online', '🟢') if cfg['events'].get(k, True) else emojis.get('offline', '🔴')} {config.ANTINUKE_EVENT_LABELS[k]}"
            for k in config.ANTINUKE_EVENT_KEYS
        )
        log_ch = ctx.guild.get_channel(cfg["log_channel"]) if cfg["log_channel"] else None
        overview = (
            f"**Status:** {emojis.get('online', '🟢') + ' Enabled' if cfg['enabled'] else emojis.get('offline', '🔴') + ' Disabled'}\n"
            f"**Punishment:** `{cfg['punishment']}`\n"
            f"**Log Channel:** {log_ch.mention if log_ch else 'Not set'}\n"
            f"**Extraowners:** {len(cfg['extraowners'])} • **Whitelisted:** {len(cfg['whitelist'])} • **Mainroles:** {len(cfg['mainroles'])}"
        )
        stats_block = "\n".join(f"{config.ANTINUKE_EVENT_LABELS[k]}: **{v}**" for k, v in stats.items()) or "No incidents logged yet."

        view = embeds.SectionLayout(f"Anti-Nuke Status — {ctx.guild.name}", [overview, events_block, stats_block])
        await ctx.send(view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiNuke(bot))
