import discord
from discord.ext import commands

from utils import database
from utils import embeds
from utils import emojis


class Profile(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="profile", description="Your custom bot profile", invoke_without_command=True)
    async def profile(self, ctx: commands.Context, member: discord.Member = None):
        await self.profile_card(ctx, member)

    @profile.command(name="card", description="View a member's profile card")
    async def profile_card(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        data = await database.get_profile(target.id)
        lines = [
            data["description"] or "No bio set.",
            f"**Social:** {data['social'] or 'Not set'}",
        ]
        await ctx.send(view=embeds.ProfileCard(
            f"{target.display_name}'s Profile", target.display_avatar.url, lines, emoji_key="cat_profiles",
        ))

    @profile.command(name="description", description="Set your profile bio")
    async def profile_description(self, ctx: commands.Context, *, text: str):
        await database.set_profile(ctx.author.id, description=text[:300])
        await ctx.send(view=embeds.success("Bio Updated"), ephemeral=True)

    @profile.command(name="social", description="Set a social link on your profile")
    async def profile_social(self, ctx: commands.Context, *, link: str):
        await database.set_profile(ctx.author.id, social=link[:200])
        await ctx.send(view=embeds.success("Social Link Updated"), ephemeral=True)

    @profile.command(name="reset", description="Reset your profile")
    async def profile_reset(self, ctx: commands.Context):
        await database.reset_profile(ctx.author.id)
        await ctx.send(view=embeds.success("Profile Reset"), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
