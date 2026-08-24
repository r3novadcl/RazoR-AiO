import discord
from discord.ext import commands

import config
from utils import database
from utils import embeds
from utils import emojis


class J2CSetupWizard(discord.ui.LayoutView):
    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.trigger_channel_id: int | None = None
        self.category_id: int | None = None

        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(
            f"{emojis.get('cat_join2create', '🔊')} **Join-to-Create Setup**\n"
            "Pick the trigger voice channel (members joining it get their own channel) "
            "and the category new channels should be created under."
        ))
        row1 = discord.ui.ActionRow()
        row1.add_item(TriggerSelect(self))
        container.add_item(row1)
        row2 = discord.ui.ActionRow()
        row2.add_item(CategorySelect(self))
        container.add_item(row2)
        row3 = discord.ui.ActionRow()
        row3.add_item(FinishButton(self))
        container.add_item(row3)
        self.add_item(container)


class TriggerSelect(discord.ui.ChannelSelect):
    def __init__(self, wizard: J2CSetupWizard):
        super().__init__(placeholder="Trigger voice channel", channel_types=[discord.ChannelType.voice])
        self.wizard = wizard

    async def callback(self, interaction: discord.Interaction):
        self.wizard.trigger_channel_id = self.values[0].id
        await interaction.response.defer()


class CategorySelect(discord.ui.ChannelSelect):
    def __init__(self, wizard: J2CSetupWizard):
        super().__init__(placeholder="Category for new channels", channel_types=[discord.ChannelType.category])
        self.wizard = wizard

    async def callback(self, interaction: discord.Interaction):
        self.wizard.category_id = self.values[0].id
        await interaction.response.defer()


class FinishButton(discord.ui.Button):
    def __init__(self, wizard: J2CSetupWizard):
        super().__init__(label="Save Configuration", style=discord.ButtonStyle.success)
        self.wizard = wizard

    async def callback(self, interaction: discord.Interaction):
        wizard = self.wizard
        if not (wizard.trigger_channel_id and wizard.category_id):
            await interaction.response.send_message(view=embeds.error("Incomplete", "Pick both a trigger channel and a category first."), ephemeral=True)
            return
        await database.set_j2c_config(wizard.guild_id, trigger_channel_id=wizard.trigger_channel_id, category_id=wizard.category_id)
        await interaction.response.edit_message(view=embeds.success("Join-to-Create Configured"))


class LimitModal(discord.ui.Modal, title="Set Channel Limit"):
    amount = discord.ui.TextInput(label="User limit (0 = unlimited)", max_length=2)

    def __init__(self, channel: discord.VoiceChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = max(0, min(99, int(self.amount.value)))
        except ValueError:
            await interaction.response.send_message(view=embeds.error("Invalid Number"), ephemeral=True)
            return
        await self.channel.edit(user_limit=value)
        await interaction.response.send_message(view=embeds.success("Limit Updated", f"{value if value else 'No'} limit"), ephemeral=True)


class RenameModal(discord.ui.Modal, title="Rename Channel"):
    name = discord.ui.TextInput(label="New channel name", max_length=100)

    def __init__(self, channel: discord.VoiceChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        await self.channel.edit(name=str(self.name.value)[:100])
        await interaction.response.send_message(view=embeds.success("Channel Renamed", str(self.name.value)), ephemeral=True)


class PanelButton(discord.ui.Button):
    def __init__(self, label: str, action: str, style=discord.ButtonStyle.secondary):
        super().__init__(label=label, style=style)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        cog: JoinToCreate = interaction.client.get_cog("JoinToCreate")
        await cog.handle_panel_action(interaction, self.action)


class J2CPanel(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=180)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(
            f"{emojis.get('cat_join2create', '🔊')} **Your Voice Channel**\nJoin your own created channel first, then use the buttons below."
        ))
        row1 = discord.ui.ActionRow()
        row1.add_item(PanelButton("Lock", "lock"))
        row1.add_item(PanelButton("Unlock", "unlock"))
        row1.add_item(PanelButton("Claim", "claim"))
        container.add_item(row1)
        row2 = discord.ui.ActionRow()
        row2.add_item(PanelButton("Set Limit", "limit", discord.ButtonStyle.primary))
        row2.add_item(PanelButton("Rename", "rename", discord.ButtonStyle.primary))
        container.add_item(row2)
        self.add_item(container)


class JoinToCreate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="j2c", description="Configure join-to-create voice channels", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def j2c(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @j2c.command(name="setup", description="Open the guided join-to-create setup wizard")
    @commands.has_permissions(administrator=True)
    async def j2c_setup(self, ctx: commands.Context):
        await ctx.send(view=J2CSetupWizard(ctx.guild.id), ephemeral=True)

    @j2c.command(name="panel", description="Open your voice channel control panel")
    async def j2c_panel(self, ctx: commands.Context):
        await ctx.send(view=J2CPanel(), ephemeral=True)

    async def _owned_channel(self, member: discord.Member) -> discord.VoiceChannel | None:
        if member.voice is None or member.voice.channel is None:
            return None
        entry = await database.get_j2c_channel(member.voice.channel.id)
        if entry is None or entry["owner_id"] != member.id:
            return None
        return member.voice.channel

    async def handle_panel_action(self, interaction: discord.Interaction, action: str) -> None:
        member = interaction.user
        guild = interaction.guild

        if action == "claim":
            if member.voice is None:
                await interaction.response.send_message(view=embeds.error("Not in a Voice Channel"), ephemeral=True)
                return
            entry = await database.get_j2c_channel(member.voice.channel.id)
            if entry is None:
                await interaction.response.send_message(view=embeds.error("Not a Join-to-Create Channel"), ephemeral=True)
                return
            owner_present = any(m.id == entry["owner_id"] for m in member.voice.channel.members)
            if owner_present:
                await interaction.response.send_message(view=embeds.error("Owner Present", "The original owner is still in the channel."), ephemeral=True)
                return
            await database.register_j2c_channel(member.voice.channel.id, guild.id, member.id)
            await interaction.response.send_message(view=embeds.success("Channel Claimed"), ephemeral=True)
            return

        channel = await self._owned_channel(member)
        if channel is None:
            await interaction.response.send_message(view=embeds.error("Not Your Channel", "Join a channel you created via join-to-create first."), ephemeral=True)
            return

        if action == "lock":
            await channel.set_permissions(guild.default_role, connect=False)
            await interaction.response.send_message(view=embeds.success("Channel Locked"), ephemeral=True)
        elif action == "unlock":
            await channel.set_permissions(guild.default_role, connect=True)
            await interaction.response.send_message(view=embeds.success("Channel Unlocked"), ephemeral=True)
        elif action == "limit":
            await interaction.response.send_modal(LimitModal(channel))
        elif action == "rename":
            await interaction.response.send_modal(RenameModal(channel))

    @commands.hybrid_command(name="voicekick", description="Kick a member from your voice channel")
    async def voicekick(self, ctx: commands.Context, member: discord.Member):
        channel = await self._owned_channel(ctx.author)
        if channel is None:
            await ctx.send(view=embeds.error("Not Your Channel", "Join a channel you created via join-to-create first."), ephemeral=True)
            return
        if member.voice and member.voice.channel and member.voice.channel.id == channel.id:
            await member.move_to(None)
        await ctx.send(view=embeds.success("Member Kicked", member.mention), ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        cfg = await database.get_j2c_config(member.guild.id)

        if cfg["trigger_channel_id"] and after.channel and after.channel.id == cfg["trigger_channel_id"]:
            category = member.guild.get_channel(cfg["category_id"]) if cfg["category_id"] else None
            new_channel = await member.guild.create_voice_channel(
                name=f"{member.display_name}'s Channel", category=category,
                overwrites={member: discord.PermissionOverwrite(manage_channels=True, move_members=True)},
            )
            await database.register_j2c_channel(new_channel.id, member.guild.id, member.id)
            try:
                await member.move_to(new_channel)
            except discord.HTTPException:
                pass

        if before.channel:
            entry = await database.get_j2c_channel(before.channel.id)
            if entry and len(before.channel.members) == 0:
                await database.remove_j2c_channel(before.channel.id)
                try:
                    await before.channel.delete(reason="Join-to-create channel empty")
                except discord.HTTPException:
                    pass


async def setup(bot: commands.Bot):
    await bot.add_cog(JoinToCreate(bot))
