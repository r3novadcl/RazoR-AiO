import discord
from discord.ext import commands

import config
from utils import embeds
from utils import emojis


class AvatarView(discord.ui.LayoutView):
    def __init__(self, target: discord.Member):
        super().__init__(timeout=180)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(f"{emojis.get('cat_profiles', '🖼️')} **{target.display_name}'s Avatar**"))
        container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(media=target.display_avatar.url)))
        self.add_item(container)


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Check the bot's latency")
    async def ping(self, ctx: commands.Context):
        await ctx.send(view=embeds.info("Pong!", f"Latency: `{round(self.bot.latency * 1000)}ms`"))

    @commands.hybrid_command(name="botinfo", description="Information about the bot")
    async def botinfo(self, ctx: commands.Context):
        view = embeds.SectionLayout(
            f"{config.BOT_NAME}",
            [
                f"**Servers:** {len(self.bot.guilds)}\n**Users:** {sum(g.member_count or 0 for g in self.bot.guilds)}",
                f"**Latency:** {round(self.bot.latency * 1000)}ms\n**discord.py:** {discord.__version__}",
            ],
            emoji_key="cat_information",
        )
        await ctx.send(view=view)

    @commands.hybrid_command(name="avatar", description="Show a member's avatar")
    async def avatar(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        await ctx.send(view=AvatarView(target))

    @commands.hybrid_command(name="userinfo", description="Information about a member")
    async def userinfo(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        view = embeds.ProfileCard(
            f"{target}", target.display_avatar.url,
            [
                f"**ID:** `{target.id}`\n**Joined Server:** {discord.utils.format_dt(target.joined_at, 'R')}",
                f"**Account Created:** {discord.utils.format_dt(target.created_at, 'R')}\n**Top Role:** {target.top_role.mention}",
            ],
            emoji_key="cat_information",
        )
        await ctx.send(view=view)

    @commands.hybrid_command(name="serverinfo", description="Information about this server")
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        blocks = [
            f"**Owner:** <@{guild.owner_id}>\n**Members:** {guild.member_count}",
            f"**Created:** {discord.utils.format_dt(guild.created_at, 'R')}\n**Roles:** {len(guild.roles)} • **Channels:** {len(guild.channels)}",
        ]
        if guild.icon:
            view = embeds.ProfileCard(guild.name, guild.icon.url, blocks, emoji_key="cat_information")
        else:
            view = embeds.SectionLayout(guild.name, blocks, emoji_key="cat_information")
        await ctx.send(view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
