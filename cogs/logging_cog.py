import discord
from discord.ext import commands

import config
from utils import database
from utils import embeds
from utils import emojis


class LogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, guild_id: int, field: str, placeholder: str):
        super().__init__(placeholder=placeholder, channel_types=[discord.ChannelType.text])
        self.guild_id = guild_id
        self.field = field

    async def callback(self, interaction: discord.Interaction):
        await database.set_logging_config(self.guild_id, **{self.field: self.values[0].id})
        await interaction.response.send_message(view=embeds.success("Updated", f"{self.placeholder} → {self.values[0].mention}"), ephemeral=True)


class LoggingSetupView(discord.ui.LayoutView):
    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(f"{emojis.get('cat_logging', '📜')} **Logging Setup**\nPick a channel for each event category below."))
        for field, label in (
            ("message_events_channel", "Message edit/delete logs"),
            ("member_events_channel", "Member join/leave logs"),
            ("voice_events_channel", "Voice join/leave/move logs"),
        ):
            row = discord.ui.ActionRow()
            row.add_item(LogChannelSelect(guild_id, field, label))
            container.add_item(row)
        self.add_item(container)


class LoggingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="logging", description="Configure event logging channels", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def logging_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @logging_group.command(name="setup", description="Open the guided logging setup (all channels at once)")
    @commands.has_permissions(administrator=True)
    async def logging_setup(self, ctx: commands.Context):
        await ctx.send(view=LoggingSetupView(ctx.guild.id), ephemeral=True)

    @logging_group.command(name="messages", description="Set the channel for message edit/delete logs")
    @commands.has_permissions(administrator=True)
    async def logging_messages(self, ctx: commands.Context, channel: discord.TextChannel):
        await database.set_logging_config(ctx.guild.id, message_events_channel=channel.id)
        await ctx.send(view=embeds.success("Message Logging Set", channel.mention), ephemeral=True)

    @logging_group.command(name="members", description="Set the channel for member join/leave logs")
    @commands.has_permissions(administrator=True)
    async def logging_members(self, ctx: commands.Context, channel: discord.TextChannel):
        await database.set_logging_config(ctx.guild.id, member_events_channel=channel.id)
        await ctx.send(view=embeds.success("Member Logging Set", channel.mention), ephemeral=True)

    @logging_group.command(name="voice", description="Set the channel for voice join/leave/move logs")
    @commands.has_permissions(administrator=True)
    async def logging_voice(self, ctx: commands.Context, channel: discord.TextChannel):
        await database.set_logging_config(ctx.guild.id, voice_events_channel=channel.id)
        await ctx.send(view=embeds.success("Voice Logging Set", channel.mention), ephemeral=True)

    async def _send(self, guild: discord.Guild, key: str, view: discord.ui.LayoutView):
        cfg = await database.get_logging_config(guild.id)
        channel_id = cfg.get(key)
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if channel is None:
            return
        try:
            await channel.send(view=view)
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot or before.content == after.content:
            return
        view = embeds.info(
            "Message Edited",
            f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n"
            f"**Before:** {before.content[:400]}\n**After:** {after.content[:400]}",
        )
        await self._send(before.guild, "message_events_channel", view)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        view = embeds.warning(
            "Message Deleted",
            f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content[:400]}",
        )
        await self._send(message.guild, "message_events_channel", view)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._send(member.guild, "member_events_channel", embeds.success("Member Joined", f"{member.mention} (`{member.id}`)"))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._send(member.guild, "member_events_channel", embeds.warning("Member Left", f"{member} (`{member.id}`)"))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel == after.channel:
            return
        if before.channel is None:
            detail = f"{member.mention} joined {after.channel.mention}"
        elif after.channel is None:
            detail = f"{member.mention} left {before.channel.mention}"
        else:
            detail = f"{member.mention} moved {before.channel.mention} → {after.channel.mention}"
        await self._send(member.guild, "voice_events_channel", embeds.info("Voice Update", detail))


async def setup(bot: commands.Bot):
    await bot.add_cog(LoggingCog(bot))
