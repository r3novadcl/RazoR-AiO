import discord
from discord.ext import commands

from utils import database
from utils import embeds
from utils import emojis


def render(template: str, member: discord.Member) -> str:
    return (
        template.replace("{user}", member.mention)
        .replace("{username}", member.display_name)
        .replace("{server}", member.guild.name)
        .replace("{membercount}", str(member.guild.member_count))
    )


class WelcomeEditModal(discord.ui.Modal, title="Edit Welcome Message"):
    def __init__(self, guild_id: int, current: str):
        super().__init__()
        self.guild_id = guild_id
        self.message = discord.ui.TextInput(
            label="Message ({user}/{server}/{membercount})", style=discord.TextStyle.paragraph,
            default=current, max_length=1000,
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        await database.set_welcome_config(self.guild_id, message=str(self.message.value))
        await interaction.response.send_message(view=embeds.success("Welcome Message Updated"), ephemeral=True)


class LeaveEditModal(discord.ui.Modal, title="Edit Leave Message"):
    def __init__(self, guild_id: int, current: str):
        super().__init__()
        self.guild_id = guild_id
        self.message = discord.ui.TextInput(
            label="Message ({user}/{server}/{membercount})", style=discord.TextStyle.paragraph,
            default=current, max_length=1000,
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        await database.set_leave_config(self.guild_id, message=str(self.message.value))
        await interaction.response.send_message(view=embeds.success("Leave Message Updated"), ephemeral=True)


class WelcomeEditButton(discord.ui.Button):
    def __init__(self, guild_id: int, current: str):
        super().__init__(label="Edit Message", style=discord.ButtonStyle.primary)
        self.guild_id = guild_id
        self.current = current

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(WelcomeEditModal(self.guild_id, self.current))


class WelcomeEditView(discord.ui.LayoutView):
    def __init__(self, guild_id: int, current: str):
        super().__init__(timeout=180)
        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(f"**Current welcome message:**\n{current}"))
        row = discord.ui.ActionRow()
        row.add_item(WelcomeEditButton(guild_id, current))
        container.add_item(row)
        self.add_item(container)


class LeaveEditButton(discord.ui.Button):
    def __init__(self, guild_id: int, current: str):
        super().__init__(label="Edit Message", style=discord.ButtonStyle.primary)
        self.guild_id = guild_id
        self.current = current

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(LeaveEditModal(self.guild_id, self.current))


class LeaveEditView(discord.ui.LayoutView):
    def __init__(self, guild_id: int, current: str):
        super().__init__(timeout=180)
        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(f"**Current leave message:**\n{current}"))
        row = discord.ui.ActionRow()
        row.add_item(LeaveEditButton(guild_id, current))
        container.add_item(row)
        self.add_item(container)


class WelcomeLeave(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="welcome", description="Configure welcome messages", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @welcome.command(name="setup", description="Enable welcome messages in a channel")
    @commands.has_permissions(administrator=True)
    async def welcome_setup(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str = None):
        cfg = await database.set_welcome_config(
            ctx.guild.id, enabled=True, channel_id=channel.id,
            message=message or "Welcome {user} to {server}! We are now {membercount} members.",
        )
        await ctx.send(view=embeds.success("Welcome Configured", f"Channel: {channel.mention}\nMessage: {cfg['message']}"), ephemeral=True)

    @welcome.command(name="edit", description="Quickly edit the welcome message text")
    @commands.has_permissions(administrator=True)
    async def welcome_edit(self, ctx: commands.Context):
        cfg = await database.get_welcome_config(ctx.guild.id)
        await ctx.send(view=WelcomeEditView(ctx.guild.id, cfg["message"]), ephemeral=True)

    @welcome.command(name="disable", description="Turn off welcome messages")
    @commands.has_permissions(administrator=True)
    async def welcome_disable(self, ctx: commands.Context):
        await database.set_welcome_config(ctx.guild.id, enabled=False)
        await ctx.send(view=embeds.warning("Welcome Messages Disabled"), ephemeral=True)

    @welcome.command(name="status", description="View the current welcome configuration")
    async def welcome_status(self, ctx: commands.Context):
        cfg = await database.get_welcome_config(ctx.guild.id)
        channel = ctx.guild.get_channel(cfg["channel_id"]) if cfg["channel_id"] else None
        state = f"{emojis.get('online', '🟢')} Enabled" if cfg["enabled"] else f"{emojis.get('offline', '🔴')} Disabled"
        await ctx.send(view=embeds.SectionLayout("Welcome Status", [f"**Status:** {state}\n**Channel:** {channel.mention if channel else 'Not set'}", cfg["message"]]), ephemeral=True)

    @commands.hybrid_group(name="leave", description="Configure leave messages", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def leave(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @leave.command(name="setup", description="Enable leave messages in a channel")
    @commands.has_permissions(administrator=True)
    async def leave_setup(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str = None):
        cfg = await database.set_leave_config(
            ctx.guild.id, enabled=True, channel_id=channel.id,
            message=message or "{user} has left {server}. We are now {membercount} members.",
        )
        await ctx.send(view=embeds.success("Leave Messages Configured", f"Channel: {channel.mention}\nMessage: {cfg['message']}"), ephemeral=True)

    @leave.command(name="edit", description="Quickly edit the leave message text")
    @commands.has_permissions(administrator=True)
    async def leave_edit(self, ctx: commands.Context):
        cfg = await database.get_leave_config(ctx.guild.id)
        await ctx.send(view=LeaveEditView(ctx.guild.id, cfg["message"]), ephemeral=True)

    @leave.command(name="disable", description="Turn off leave messages")
    @commands.has_permissions(administrator=True)
    async def leave_disable(self, ctx: commands.Context):
        await database.set_leave_config(ctx.guild.id, enabled=False)
        await ctx.send(view=embeds.warning("Leave Messages Disabled"), ephemeral=True)

    @leave.command(name="status", description="View the current leave configuration")
    async def leave_status(self, ctx: commands.Context):
        cfg = await database.get_leave_config(ctx.guild.id)
        channel = ctx.guild.get_channel(cfg["channel_id"]) if cfg["channel_id"] else None
        state = f"{emojis.get('online', '🟢')} Enabled" if cfg["enabled"] else f"{emojis.get('offline', '🔴')} Disabled"
        await ctx.send(view=embeds.SectionLayout("Leave Status", [f"**Status:** {state}\n**Channel:** {channel.mention if channel else 'Not set'}", cfg["message"]]), ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cfg = await database.get_welcome_config(member.guild.id)
        if not cfg["enabled"] or not cfg["channel_id"]:
            return
        channel = member.guild.get_channel(cfg["channel_id"])
        if channel is None:
            return
        try:
            await channel.send(view=embeds.success("Welcome!", render(cfg["message"], member)))
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        cfg = await database.get_leave_config(member.guild.id)
        if not cfg["enabled"] or not cfg["channel_id"]:
            return
        channel = member.guild.get_channel(cfg["channel_id"])
        if channel is None:
            return
        try:
            await channel.send(view=embeds.info("Goodbye", render(cfg["message"], member)))
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeLeave(bot))
