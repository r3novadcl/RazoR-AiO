import time

import discord
from discord.ext import commands, tasks

import config
from utils import database
from utils import embeds
from utils import emojis
from utils import raid
from utils.checks import is_owner_or_extraowner


class AntiRaidSetupModal(discord.ui.Modal, title="Anti-Raid Configuration"):
    join_threshold = discord.ui.TextInput(label="Join threshold (accounts)", placeholder="10", max_length=3)
    join_window = discord.ui.TextInput(label="Time window (seconds)", placeholder="15", max_length=4)
    lockdown_minutes = discord.ui.TextInput(label="Auto-unlock after (minutes)", placeholder="15", max_length=4)
    new_account_days = discord.ui.TextInput(label="Flag accounts younger than (days)", placeholder="3", max_length=3)

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            values = {
                "join_threshold": int(self.join_threshold.value),
                "join_window_seconds": int(self.join_window.value),
                "lockdown_minutes": int(self.lockdown_minutes.value),
                "new_account_max_age_days": int(self.new_account_days.value),
            }
        except ValueError:
            await interaction.response.send_message(view=embeds.error("Invalid Input", "All fields must be numbers."), ephemeral=True)
            return
        await database.set_antiraid_config(self.guild_id, **values)
        await interaction.response.send_message(view=embeds.success("Anti-Raid Configured", "Detection thresholds updated."), ephemeral=True)


class AlertChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, guild_id: int):
        super().__init__(placeholder="Choose the raid alert channel", channel_types=[discord.ChannelType.text])
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        await database.set_antiraid_config(self.guild_id, alert_channel_id=self.values[0].id)
        await interaction.response.send_message(view=embeds.success("Alert Channel Set", self.values[0].mention), ephemeral=True)


class SetupWizardView(discord.ui.LayoutView):
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(
            f"{emojis.get('shield', '🛡️')} **Anti-Raid Setup**\n"
            "Step 1 — set your detection thresholds with the button below.\n"
            "Step 2 — pick the channel raid alerts should go to."
        ))
        row1 = discord.ui.ActionRow()
        row1.add_item(ConfigureButton(guild_id))
        container.add_item(row1)
        row2 = discord.ui.ActionRow()
        row2.add_item(AlertChannelSelect(guild_id))
        container.add_item(row2)
        self.add_item(container)


class ConfigureButton(discord.ui.Button):
    def __init__(self, guild_id: int):
        super().__init__(label="Configure Thresholds", style=discord.ButtonStyle.primary)
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AntiRaidSetupModal(self.guild_id))


class AntiRaid(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._join_windows: dict[int, list[float]] = {}
        self.auto_unlock_loop.start()

    def cog_unload(self) -> None:
        self.auto_unlock_loop.cancel()

    @commands.hybrid_group(name="antiraid", description="Configure raid protection and lockdown", invoke_without_command=True)
    async def antiraid(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @antiraid.command(name="setup", description="Open the anti-raid setup wizard")
    @is_owner_or_extraowner()
    async def antiraid_setup(self, ctx: commands.Context):
        await ctx.send(view=SetupWizardView(ctx.guild.id), ephemeral=True)

    @antiraid.command(name="enable", description="Enable raid protection")
    @is_owner_or_extraowner()
    async def antiraid_enable(self, ctx: commands.Context):
        await database.set_antiraid_config(ctx.guild.id, enabled=True)
        await ctx.send(view=embeds.success("Anti-Raid Enabled"), ephemeral=True)

    @antiraid.command(name="disable", description="Disable raid protection")
    @is_owner_or_extraowner()
    async def antiraid_disable(self, ctx: commands.Context):
        await database.set_antiraid_config(ctx.guild.id, enabled=False)
        await ctx.send(view=embeds.warning("Anti-Raid Disabled"), ephemeral=True)

    @antiraid.command(name="status", description="View anti-raid configuration and lockdown state")
    async def antiraid_status(self, ctx: commands.Context):
        cfg = await database.get_antiraid_config(ctx.guild.id)
        lockdown = await database.get_lockdown(ctx.guild.id)
        alert_ch = ctx.guild.get_channel(cfg["alert_channel_id"]) if cfg["alert_channel_id"] else None

        overview = (
            f"**Status:** {(emojis.get('online', '🟢') + ' Enabled') if cfg['enabled'] else (emojis.get('offline', '🔴') + ' Disabled')}\n"
            f"**Threshold:** {cfg['join_threshold']} joins / {cfg['join_window_seconds']}s\n"
            f"**Auto-unlock:** {cfg['lockdown_minutes']} minutes\n"
            f"**Auto-kick new accounts:** {'Yes' if cfg['auto_kick_new_accounts'] else 'No'} (< {cfg['new_account_max_age_days']}d old)\n"
            f"**Alert Channel:** {alert_ch.mention if alert_ch else 'Not set'}"
        )
        lock_block = f"{emojis.get('lock', '🔒')} **Currently in lockdown**" if lockdown else f"{emojis.get('unlock', '🔓')} Not currently locked down"
        await ctx.send(view=embeds.SectionLayout("Anti-Raid Status", [overview, lock_block]), ephemeral=True)

    @antiraid.command(name="panic", description="Manually lock down the entire server immediately")
    @is_owner_or_extraowner()
    async def antiraid_panic(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        locked = await raid.lockdown_guild(ctx.guild, reason=f"Panic mode triggered by {ctx.author}")
        await raid.notify_owner_and_extraowners(
            ctx.guild, f"{emojis.get('siren', '🚨')} Panic Mode Activated", f"Triggered manually by {ctx.author}. {locked} channel(s) locked."
        )
        await ctx.send(view=embeds.alert("Panic Mode Activated", f"{locked} channel(s) locked down. Use `/antiraid unlock` when it's safe."), ephemeral=True)

    @antiraid.command(name="unlock", description="Lift an active lockdown")
    @is_owner_or_extraowner()
    async def antiraid_unlock(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        restored = await raid.unlock_guild(ctx.guild)
        if restored == 0:
            await ctx.send(view=embeds.info("Not Locked Down", "This server isn't currently in lockdown."), ephemeral=True)
            return
        await ctx.send(view=embeds.success("Lockdown Lifted", f"{restored} channel(s) restored."), ephemeral=True)

    async def _alert(self, guild: discord.Guild, view: discord.ui.LayoutView) -> None:
        cfg = await database.get_antiraid_config(guild.id)
        if not cfg["alert_channel_id"]:
            return
        channel = guild.get_channel(cfg["alert_channel_id"])
        if channel:
            try:
                await channel.send(view=view)
            except discord.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        cfg = await database.get_antiraid_config(guild.id)
        if not cfg["enabled"]:
            return

        now = time.time()
        joins = [t for t in self._join_windows.get(guild.id, []) if now - t < cfg["join_window_seconds"]]
        joins.append(now)
        self._join_windows[guild.id] = joins

        account_age_days = (now - member.created_at.timestamp()) / 86400
        if cfg["auto_kick_new_accounts"] and account_age_days < cfg["new_account_max_age_days"] and len(joins) >= max(2, cfg["join_threshold"] // 2):
            try:
                await member.kick(reason="Anti-Raid: new account during elevated join activity")
            except discord.Forbidden:
                pass

        if len(joins) < cfg["join_threshold"]:
            return

        existing_lockdown = await database.get_lockdown(guild.id)
        if existing_lockdown:
            return

        locked = await raid.lockdown_guild(guild, reason="Anti-Raid: automatic lockdown, join-rate threshold exceeded")
        self._join_windows[guild.id] = []

        await raid.notify_owner_and_extraowners(
            guild, f"{emojis.get('siren', '🚨')} Raid Detected — Server Locked Down",
            f"{len(joins)} joins in {cfg['join_window_seconds']}s exceeded the threshold. "
            f"{locked} channel(s) locked automatically. It will auto-unlock in {cfg['lockdown_minutes']} minutes, "
            "or run `/antiraid unlock` once you've confirmed it's safe.",
        )
        await self._alert(guild, embeds.alert(
            "Raid Lockdown Active",
            f"{len(joins)} joins in {cfg['join_window_seconds']}s. {locked} channel(s) locked. "
            f"Auto-unlock in {cfg['lockdown_minutes']} minutes.",
        ))

    @tasks.loop(minutes=1)
    async def auto_unlock_loop(self):
        for lockdown in await database.get_active_lockdowns():
            guild = self.bot.get_guild(lockdown["guild_id"])
            if guild is None:
                continue
            cfg = await database.get_antiraid_config(guild.id)
            elapsed_minutes = (time.time() - lockdown["started_at"]) / 60
            if elapsed_minutes >= cfg["lockdown_minutes"]:
                restored = await raid.unlock_guild(guild)
                await self._alert(guild, embeds.success("Lockdown Auto-Lifted", f"{restored} channel(s) restored after {cfg['lockdown_minutes']} minutes."))

    @auto_unlock_loop.before_loop
    async def before_auto_unlock_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiRaid(bot))
