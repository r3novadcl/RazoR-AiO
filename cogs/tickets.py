import discord
from discord.ext import commands

import config
from utils import emojis
from utils import database
from utils import embeds


class TicketPanelView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(f"{emojis.get('ticket', '🎫')} **Support Tickets**\nClick below to open a private ticket with staff."))
        action_row = discord.ui.ActionRow()
        action_row.add_item(OpenTicketButton())
        container.add_item(action_row)
        self.add_item(container)


class OpenTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Open Ticket", style=discord.ButtonStyle.primary, custom_id="razor:ticket:open")

    async def callback(self, interaction: discord.Interaction):
        cog: Tickets = interaction.client.get_cog("Tickets")
        await cog.open_ticket(interaction)


class CloseTicketView(discord.ui.LayoutView):
    def __init__(self, opener: discord.abc.User | None = None):
        super().__init__(timeout=None)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR_ALERT)
        intro = f"{opener.mention} — welcome to your ticket.\n" if opener else ""
        container.add_item(discord.ui.TextDisplay(f"{intro}Use the button below to close this ticket."))
        action_row = discord.ui.ActionRow()
        action_row.add_item(CloseTicketButton())
        container.add_item(action_row)
        self.add_item(container)


class CloseTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="razor:ticket:close")

    async def callback(self, interaction: discord.Interaction):
        cog: Tickets = interaction.client.get_cog("Tickets")
        await cog.close_ticket(interaction)


class TicketSetupWizard(discord.ui.LayoutView):
    def __init__(self, guild_id: int, channel_id: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.category_id: int | None = None
        self.support_role_id: int | None = None
        self.log_channel_id: int | None = None

        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(
            f"{emojis.get('ticket', '🎫')} **Ticket System Setup**\n"
            "Pick a category, support role, and log channel below, then hit **Finish & Post Panel** "
            "to publish the ticket-opening panel in this channel."
        ))
        row1 = discord.ui.ActionRow()
        row1.add_item(CategorySelect(self))
        container.add_item(row1)
        row2 = discord.ui.ActionRow()
        row2.add_item(SupportRoleSelect(self))
        container.add_item(row2)
        row3 = discord.ui.ActionRow()
        row3.add_item(LogChannelSelect(self))
        container.add_item(row3)
        row4 = discord.ui.ActionRow()
        row4.add_item(FinishButton(self))
        container.add_item(row4)
        self.add_item(container)


class CategorySelect(discord.ui.ChannelSelect):
    def __init__(self, wizard: TicketSetupWizard):
        super().__init__(placeholder="Ticket category", channel_types=[discord.ChannelType.category])
        self.wizard = wizard

    async def callback(self, interaction: discord.Interaction):
        self.wizard.category_id = self.values[0].id
        await interaction.response.defer()


class SupportRoleSelect(discord.ui.RoleSelect):
    def __init__(self, wizard: TicketSetupWizard):
        super().__init__(placeholder="Support/staff role")
        self.wizard = wizard

    async def callback(self, interaction: discord.Interaction):
        self.wizard.support_role_id = self.values[0].id
        await interaction.response.defer()


class LogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, wizard: TicketSetupWizard):
        super().__init__(placeholder="Ticket log channel", channel_types=[discord.ChannelType.text])
        self.wizard = wizard

    async def callback(self, interaction: discord.Interaction):
        self.wizard.log_channel_id = self.values[0].id
        await interaction.response.defer()


class FinishButton(discord.ui.Button):
    def __init__(self, wizard: TicketSetupWizard):
        super().__init__(label="Finish & Post Panel", style=discord.ButtonStyle.success)
        self.wizard = wizard

    async def callback(self, interaction: discord.Interaction):
        wizard = self.wizard
        if not (wizard.category_id and wizard.support_role_id and wizard.log_channel_id):
            await interaction.response.send_message(
                view=embeds.error("Incomplete", "Pick a category, support role, and log channel first."), ephemeral=True
            )
            return

        await database.set_tickets_config(
            wizard.guild_id, category_id=wizard.category_id,
            support_role_id=wizard.support_role_id, log_channel_id=wizard.log_channel_id,
        )
        channel = interaction.guild.get_channel(wizard.channel_id)
        panel_message = await channel.send(view=TicketPanelView())
        await database.set_tickets_config(wizard.guild_id, panel_channel_id=channel.id, panel_message_id=panel_message.id)

        await interaction.response.edit_message(view=embeds.success("Tickets Configured", f"Panel posted in {channel.mention}."))


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(CloseTicketView())

    @commands.hybrid_group(name="tickets", description="Configure the ticket system", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def tickets(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @tickets.command(name="setup", description="Open the guided ticket setup wizard")
    @commands.has_permissions(administrator=True)
    async def tickets_setup(self, ctx: commands.Context):
        await ctx.send(view=TicketSetupWizard(ctx.guild.id, ctx.channel.id), ephemeral=True)

    @tickets.command(name="panel", description="Post the ticket-opening panel in this channel")
    @commands.has_permissions(administrator=True)
    async def tickets_panel(self, ctx: commands.Context):
        msg = await ctx.channel.send(view=TicketPanelView())
        await database.set_tickets_config(ctx.guild.id, panel_channel_id=ctx.channel.id, panel_message_id=msg.id)
        await ctx.send(view=embeds.success("Panel Posted"), ephemeral=True)

    @commands.hybrid_command(name="support", description="Open a support ticket directly")
    async def support(self, ctx: commands.Context):
        cfg = await database.get_tickets_config(ctx.guild.id)
        if not cfg["category_id"]:
            await ctx.send(view=embeds.error("Not Configured", "Ask an admin to run the tickets setup command first."), ephemeral=True)
            return

        category = ctx.guild.get_channel(cfg["category_id"])
        support_role = ctx.guild.get_role(cfg["support_role_id"]) if cfg["support_role_id"] else None
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            ctx.author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await ctx.guild.create_text_channel(name=f"ticket-{ctx.author.name}"[:90], category=category, overwrites=overwrites)
        await database.open_ticket(channel.id, ctx.guild.id, ctx.author.id)
        await channel.send(view=CloseTicketView(ctx.author))
        await ctx.send(view=embeds.success("Ticket Opened", channel.mention), ephemeral=True)

    async def open_ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        cfg = await database.get_tickets_config(guild.id)
        if not cfg["category_id"]:
            await interaction.response.send_message(view=embeds.error("Not Configured", "Ask an admin to run the tickets setup command first."), ephemeral=True)
            return

        category = guild.get_channel(cfg["category_id"])
        support_role = guild.get_role(cfg["support_role_id"]) if cfg["support_role_id"] else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}"[:90], category=category, overwrites=overwrites,
        )
        await database.open_ticket(channel.id, guild.id, interaction.user.id)
        await channel.send(view=CloseTicketView(interaction.user))
        await interaction.response.send_message(view=embeds.success("Ticket Opened", channel.mention), ephemeral=True)

    async def close_ticket(self, interaction: discord.Interaction):
        ticket = await database.get_ticket(interaction.channel.id)
        if ticket is None:
            await interaction.response.send_message(view=embeds.error("Not a Ticket", "This isn't an open ticket channel."), ephemeral=True)
            return

        cfg = await database.get_tickets_config(interaction.guild.id)
        log_channel = interaction.guild.get_channel(cfg["log_channel_id"]) if cfg["log_channel_id"] else None
        if log_channel:
            opener = interaction.guild.get_member(ticket["user_id"])
            await log_channel.send(view=embeds.info("Ticket Closed", f"Channel: #{interaction.channel.name}\nOpened by: {opener.mention if opener else ticket['user_id']}\nClosed by: {interaction.user.mention}"))

        await database.close_ticket(interaction.channel.id)
        await interaction.response.send_message(view=embeds.warning("Closing Ticket", "This channel will be deleted shortly."))
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
