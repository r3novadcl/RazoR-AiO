import datetime

import discord
from discord import app_commands
from discord.ext import commands

import config
from utils import database
from utils import embeds
from utils import emojis


def can_moderate(actor: discord.Member, target: discord.Member) -> bool:
    if target.id == actor.guild.owner_id:
        return False
    if target.top_role >= actor.top_role and actor.id != actor.guild.owner_id:
        return False
    return True


class ReasonModal(discord.ui.Modal):
    reason = discord.ui.TextInput(label="Reason", style=discord.TextStyle.paragraph, required=False, max_length=300, default="No reason provided")

    def __init__(self, title: str, action: str, target: discord.Member, extra_label: str | None = None):
        super().__init__(title=title)
        self.action = action
        self.target = target
        self.extra = None
        if extra_label:
            self.extra = discord.ui.TextInput(label=extra_label, max_length=4)
            self.add_item(self.extra)

    async def on_submit(self, interaction: discord.Interaction):
        cog: Moderation = interaction.client.get_cog("Moderation")
        reason = str(self.reason.value) or "No reason provided"
        extra_value = str(self.extra.value) if self.extra else None
        await cog.run_action(interaction, self.action, self.target, reason, extra_value)


class ModPanelButton(discord.ui.Button):
    def __init__(self, label: str, action: str, style: discord.ButtonStyle, target: discord.Member):
        super().__init__(label=label, style=style)
        self.action = action
        self.target = target

    async def callback(self, interaction: discord.Interaction):
        titles = {"warn": "Warn Member", "kick": "Kick Member", "ban": "Ban Member", "timeout": "Timeout Member"}
        extra = "Minutes" if self.action == "timeout" else None
        await interaction.response.send_modal(ReasonModal(titles[self.action], self.action, self.target, extra))


class ModPanel(discord.ui.LayoutView):
    def __init__(self, target: discord.Member, warning_count: int):
        super().__init__(timeout=180)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        header = discord.ui.Section(
            discord.ui.TextDisplay(
                f"{emojis.get('shield', '🔨')} **Moderation Panel — {target}**\n"
                f"`{target.id}` • Joined {discord.utils.format_dt(target.joined_at, 'R') if target.joined_at else 'unknown'} • "
                f"{warning_count} warning(s) on record"
            ),
            accessory=discord.ui.Thumbnail(media=target.display_avatar.url),
        )
        container.add_item(header)
        row1 = discord.ui.ActionRow()
        row1.add_item(ModPanelButton("Warn", "warn", discord.ButtonStyle.secondary, target))
        row1.add_item(ModPanelButton("Timeout", "timeout", discord.ButtonStyle.secondary, target))
        container.add_item(row1)
        row2 = discord.ui.ActionRow()
        row2.add_item(ModPanelButton("Kick", "kick", discord.ButtonStyle.danger, target))
        row2.add_item(ModPanelButton("Ban", "ban", discord.ButtonStyle.danger, target))
        container.add_item(row2)
        self.add_item(container)


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log(self, ctx: commands.Context, target: discord.Member, action: str, reason: str):
        await database.log_mod_action(ctx.guild.id, target.id, ctx.author.id, action, reason)
        settings = await database.get_guild_settings(ctx.guild.id)
        channel_id = settings.get("mod_log_channel")
        if not channel_id:
            return
        channel = ctx.guild.get_channel(channel_id)
        if channel is None:
            return
        view = embeds.info(
            f"Moderation: {action}",
            f"**Target:** {target.mention} (`{target.id}`)\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}",
        )
        try:
            await channel.send(view=view)
        except discord.HTTPException:
            pass

    @commands.hybrid_command(name="warn", description="Warn a member")
    @app_commands.describe(member="Member to warn", reason="Why they're being warned")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if not can_moderate(ctx.author, member):
            await ctx.send(view=embeds.error("Cannot Warn", "That member outranks you or is the owner."), ephemeral=True)
            return
        await database.add_warning(ctx.guild.id, member.id, ctx.author.id, reason)
        await self._log(ctx, member, "warn", reason)
        await ctx.send(view=embeds.success("Member Warned", f"{member.mention} — {reason}"))

    @commands.hybrid_command(name="warnings", description="View a member's warnings")
    async def warnings(self, ctx: commands.Context, member: discord.Member):
        rows = await database.get_warnings(ctx.guild.id, member.id)
        if not rows:
            await ctx.send(view=embeds.info("No Warnings", f"{member.mention} has a clean record."), ephemeral=True)
            return
        lines = [f"`#{r['id']}` — {r['reason']}" for r in rows]
        await ctx.send(view=embeds.SectionLayout(f"Warnings — {member}", lines), ephemeral=True)

    @commands.hybrid_command(name="clearwarnings", description="Clear all warnings for a member")
    @commands.has_permissions(moderate_members=True)
    async def clearwarnings(self, ctx: commands.Context, member: discord.Member):
        await database.clear_warnings(ctx.guild.id, member.id)
        await ctx.send(view=embeds.success("Warnings Cleared", member.mention), ephemeral=True)

    @commands.hybrid_command(name="kick", description="Kick a member")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if not can_moderate(ctx.author, member):
            await ctx.send(view=embeds.error("Cannot Kick", "That member outranks you or is the owner."), ephemeral=True)
            return
        await member.kick(reason=reason)
        await self._log(ctx, member, "kick", reason)
        await ctx.send(view=embeds.success("Member Kicked", f"{member.mention} — {reason}"))

    @commands.hybrid_command(name="ban", description="Ban a member")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if not can_moderate(ctx.author, member):
            await ctx.send(view=embeds.error("Cannot Ban", "That member outranks you or is the owner."), ephemeral=True)
            return
        await member.ban(reason=reason)
        await self._log(ctx, member, "ban", reason)
        await ctx.send(view=embeds.success("Member Banned", f"{member.mention} — {reason}"))

    @commands.hybrid_command(name="unban", description="Unban a user by ID")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: str, *, reason: str = "No reason provided"):
        user = discord.Object(id=int(user_id))
        await ctx.guild.unban(user, reason=reason)
        await ctx.send(view=embeds.success("User Unbanned", f"`{user_id}` — {reason}"))

    @commands.hybrid_command(name="timeout", description="Timeout a member (minutes)")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "No reason provided"):
        if not can_moderate(ctx.author, member):
            await ctx.send(view=embeds.error("Cannot Timeout", "That member outranks you or is the owner."), ephemeral=True)
            return
        await member.timeout(discord.utils.utcnow() + datetime.timedelta(minutes=minutes), reason=reason)
        await self._log(ctx, member, "timeout", f"{minutes}m — {reason}")
        await ctx.send(view=embeds.success("Member Timed Out", f"{member.mention} for {minutes}m"))

    @commands.hybrid_command(name="untimeout", description="Remove a member's timeout")
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx: commands.Context, member: discord.Member):
        await member.timeout(None)
        await ctx.send(view=embeds.success("Timeout Removed", member.mention))

    @commands.hybrid_command(name="purge", description="Bulk delete messages")
    @app_commands.describe(amount="How many messages (1-100)")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: commands.Range[int, 1, 100]):
        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=amount)
        await ctx.send(view=embeds.success("Messages Purged", f"Deleted {len(deleted)} message(s)."), ephemeral=True)

    @commands.hybrid_command(name="setmodlog", description="Set the moderation log channel")
    @commands.has_permissions(administrator=True)
    async def setmodlog(self, ctx: commands.Context, channel: discord.TextChannel):
        await database.set_guild_setting(ctx.guild.id, mod_log_channel=channel.id)
        await ctx.send(view=embeds.success("Mod Log Set", channel.mention), ephemeral=True)


    @commands.hybrid_command(name="modpanel", description="Open a quick moderation action panel for a member")
    @commands.has_permissions(moderate_members=True)
    async def modpanel(self, ctx: commands.Context, member: discord.Member):
        if not can_moderate(ctx.author, member):
            await ctx.send(view=embeds.error("Cannot Moderate", "That member outranks you or is the owner."), ephemeral=True)
            return
        warnings = await database.get_warnings(ctx.guild.id, member.id)
        await ctx.send(view=ModPanel(member, len(warnings)), ephemeral=True)

    async def run_action(self, interaction: discord.Interaction, action: str, target: discord.Member, reason: str, extra: str | None) -> None:
        guild = interaction.guild
        actor = interaction.user

        if not can_moderate(actor, target):
            await interaction.response.send_message(view=embeds.error("Cannot Moderate", "That member outranks you or is the owner."), ephemeral=True)
            return

        try:
            if action == "warn":
                await database.add_warning(guild.id, target.id, actor.id, reason)
            elif action == "kick":
                await target.kick(reason=reason)
            elif action == "ban":
                await target.ban(reason=reason)
            elif action == "timeout":
                minutes = int(extra) if extra and extra.isdigit() else 10
                await target.timeout(discord.utils.utcnow() + datetime.timedelta(minutes=minutes), reason=reason)
        except discord.Forbidden:
            await interaction.response.send_message(view=embeds.error("Missing Permissions", "The bot can't perform that action on this member."), ephemeral=True)
            return

        await database.log_mod_action(guild.id, target.id, actor.id, action, reason)
        settings = await database.get_guild_settings(guild.id)
        channel_id = settings.get("mod_log_channel")
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(view=embeds.info(f"Moderation: {action}", f"**Target:** {target.mention} (`{target.id}`)\n**Moderator:** {actor.mention}\n**Reason:** {reason}"))
                except discord.HTTPException:
                    pass

        action_labels = {"warn": "Warned", "kick": "Kicked", "ban": "Banned", "timeout": "Timed Out"}
        await interaction.response.send_message(view=embeds.success(f"Member {action_labels.get(action, action.capitalize())}", f"{target.mention} — {reason}"), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
