import discord
from discord.ext import commands

import config
from utils import database
from utils import embeds
from utils import emojis


class MatchTextModal(discord.ui.Modal, title="Vanity Match Text"):
    text = discord.ui.TextInput(label="Text to match in custom status", max_length=100)

    def __init__(self, guild_id: int, role_id: int):
        super().__init__()
        self.guild_id = guild_id
        self.role_id = role_id

    async def on_submit(self, interaction: discord.Interaction):
        await database.set_vanityroles_config(self.guild_id, match_text=str(self.text.value), role_id=self.role_id)
        role = interaction.guild.get_role(self.role_id)
        await interaction.response.send_message(
            view=embeds.success("Vanity Role Configured", f"Members with `{self.text.value}` in their status get {role.mention if role else 'the selected role'}."),
            ephemeral=True,
        )


class VanitySetupRoleSelect(discord.ui.RoleSelect):
    def __init__(self, guild_id: int):
        super().__init__(placeholder="Choose the role to grant")
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(MatchTextModal(self.guild_id, self.values[0].id))


class VanitySetupView(discord.ui.LayoutView):
    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(
            f"{emojis.get('cat_vanityroles', '✨')} **Vanity Role Setup**\n"
            "Pick the role to grant, then enter the text to match in a member's custom status."
        ))
        row = discord.ui.ActionRow()
        row.add_item(VanitySetupRoleSelect(guild_id))
        container.add_item(row)
        self.add_item(container)


class VanityRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="vanityroles", description="Grant a role when a member's status matches text", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def vanityroles(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @vanityroles.command(name="setup", description="Open the guided vanity role setup")
    @commands.has_permissions(administrator=True)
    async def vanityroles_setup(self, ctx: commands.Context):
        await ctx.send(view=VanitySetupView(ctx.guild.id), ephemeral=True)

    @vanityroles.command(name="status", description="View the current vanity role configuration")
    async def vanityroles_status(self, ctx: commands.Context):
        cfg = await database.get_vanityroles_config(ctx.guild.id)
        if not cfg["match_text"] or not cfg["role_id"]:
            await ctx.send(view=embeds.info("Not Configured", "Run `vanityroles setup` first."), ephemeral=True)
            return
        role = ctx.guild.get_role(cfg["role_id"])
        await ctx.send(view=embeds.info("Vanity Role Config", f"Match text: `{cfg['match_text']}`\nRole: {role.mention if role else 'Unknown'}"), ephemeral=True)

    @vanityroles.command(name="reset", description="Clear vanity role configuration")
    @commands.has_permissions(administrator=True)
    async def vanityroles_reset(self, ctx: commands.Context):
        await database.set_vanityroles_config(ctx.guild.id, match_text=None, role_id=None)
        await ctx.send(view=embeds.success("Vanity Role Config Cleared"), ephemeral=True)

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        cfg = await database.get_vanityroles_config(after.guild.id)
        if not cfg["match_text"] or not cfg["role_id"]:
            return

        role = after.guild.get_role(cfg["role_id"])
        if role is None:
            return

        status_text = ""
        for activity in after.activities:
            if isinstance(activity, discord.CustomActivity) and activity.name:
                status_text = activity.name
                break

        has_match = cfg["match_text"].lower() in status_text.lower()
        has_role = role in after.roles

        try:
            if has_match and not has_role:
                await after.add_roles(role, reason="Vanity role match")
            elif not has_match and has_role:
                await after.remove_roles(role, reason="Vanity role no longer matches")
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(VanityRoles(bot))
