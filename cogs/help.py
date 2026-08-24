import discord
from discord.ext import commands

import config
from utils import embeds
from utils import emojis

EXCLUDED_COGS = {"Help"}

CATEGORY_META = {
    "AI": ("AI Chat", "cat_ai", "🤖"),
    "Animals": ("Animals", "cat_animals", "🐾"),
    "AntiNuke": ("Anti-Nuke", "cat_antinuke", "🛡️"),
    "AntiRaid": ("Anti-Raid", "siren", "🚨"),
    "AutoMod": ("Auto-Mod", "cat_automod", "🧹"),
    "AutoPost": ("Auto-Post", "cat_automation", "📢"),
    "AutoReact": ("Auto-React", "cat_automation", "⚡"),
    "AutoResponder": ("Auto-Responder", "cat_automation", "💬"),
    "Conversion": ("Conversion Tools", "cat_general", "🔢"),
    "Fun": ("Fun", "cat_fun", "🎉"),
    "GitHub": ("GitHub Lookup", "cat_information", "🐙"),
    "Giveaway": ("Giveaways", "cat_giveaway", "🎁"),
    "Google": ("Google Search", "cat_information", "🔍"),
    "Ignore": ("Ignore List", "cat_misc", "🙈"),
    "Invites": ("Invite Tracking", "cat_tracking", "📨"),
    "JoinToCreate": ("Voice / J2C", "cat_join2create", "🔊"),
    "Leveling": ("Leveling", "cat_tracking", "📈"),
    "LoggingCog": ("Logging", "cat_logging", "📜"),
    "MessageStats": ("Message Stats", "cat_tracking", "💬"),
    "Moderation": ("Moderation", "cat_moderation", "🔨"),
    "Music": ("Music", "cat_media", "🎵"),
    "MentionReply": ("Mention Reply", "cat_general", "👋"),
    "OwnerTools": ("Owner Tools", "cat_general", "⚙️"),
    "Pfps": ("Profile Pictures", "cat_profiles", "🖼️"),
    "Profile": ("Profile Cards", "cat_profiles", "🪪"),
    "ReactionRoles": ("Reaction Roles", "cat_reactionroles", "🎭"),
    "Remind": ("Reminders", "cat_misc", "⏰"),
    "Roleplay": ("Roleplay", "cat_roleplay", "💞"),
    "StatsInfo": ("Server Stats", "cat_information", "📊"),
    "Steal": ("Steal Emoji/Sticker", "cat_misc", "🧲"),
    "Tickets": ("Tickets", "cat_tickets", "🎫"),
    "Todo": ("To-Do List", "cat_misc", "📝"),
    "TTS": ("Text-to-Speech", "cat_media", "🔊"),
    "Utility": ("Utility", "cat_utility", "🛠️"),
    "VanityRoles": ("Vanity Roles", "cat_vanityroles", "✨"),
    "WelcomeLeave": ("Welcome & Leave", "cat_welcome", "👋"),
    "YouTube": ("YouTube Alerts", "cat_media", "📺"),
}

HOME_VALUE = "razor:help:home"


def flatten(command) -> list[commands.Command]:
    found = []
    if isinstance(command, commands.Group):
        for sub in command.commands:
            found.extend(flatten(sub))
    else:
        found.append(command)
    return found


def cog_commands(cog: commands.Cog) -> list[commands.Command]:
    found = []
    for command in cog.get_commands():
        found.extend(flatten(command))
    return found


def category_meta(cog_name: str) -> tuple[str, str, str]:
    return CATEGORY_META.get(cog_name, (cog_name, "info", "📁"))


class CategorySelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, active: str | None = None):
        self.bot = bot
        options = [discord.SelectOption(
            label="Home", value=HOME_VALUE, description="Back to the overview",
            emoji=emojis.get("cat_home", "🏠"), default=active is None,
        )]
        for cog_name, cog in bot.cogs.items():
            if cog_name in EXCLUDED_COGS or not cog_commands(cog):
                continue
            label, emoji_key, fallback = category_meta(cog_name)
            options.append(discord.SelectOption(
                label=label, value=cog_name,
                description=f"{len(cog_commands(cog))} command(s)",
                emoji=emojis.get(emoji_key, fallback),
                default=cog_name == active,
            ))
        options = options[:1] + sorted(options[1:], key=lambda o: o.label)
        super().__init__(placeholder="Choose a category", options=options[:25], custom_id="razor:help:select")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == HOME_VALUE:
            await interaction.response.edit_message(view=HelpView(self.bot))
            return
        cog = self.bot.get_cog(self.values[0])
        if cog is None:
            await interaction.response.edit_message(view=HelpView(self.bot))
            return
        await interaction.response.edit_message(view=CategoryView(self.bot, self.values[0], cog))


class HelpView(discord.ui.LayoutView):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=180)
        eligible = [name for name, cog in bot.cogs.items() if name not in EXCLUDED_COGS and cog_commands(cog)]
        total = sum(len(cog_commands(bot.cogs[name])) for name in eligible)
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(
            f"{emojis.get('book', '📖')} **{config.BOT_NAME} Help**\n"
            f"{total} commands across {len(eligible)} categories. "
            f"Prefix: `{config.PREFIX}` — every command also works as `/slash`.\n"
            "Pick a category from the dropdown below to see its commands. "
            "You can switch categories any time without re-running the command."
        ))
        row = discord.ui.ActionRow()
        row.add_item(CategorySelect(bot))
        container.add_item(row)
        self.add_item(container)


class CategoryView(discord.ui.LayoutView):
    def __init__(self, bot: commands.Bot, cog_name: str, cog: commands.Cog):
        super().__init__(timeout=180)
        label, emoji_key, fallback = category_meta(cog_name)
        command_list = sorted(cog_commands(cog), key=lambda c: c.qualified_name)
        lines = [f"`{config.PREFIX}{c.qualified_name}` — {c.description or 'No description.'}" for c in command_list]
        container = discord.ui.Container(accent_colour=config.EMBED_COLOR)
        container.add_item(discord.ui.TextDisplay(f"{emojis.get(emoji_key, fallback)} **{label}** ({len(command_list)})"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay("\n".join(lines) or "No commands here yet."))
        row = discord.ui.ActionRow()
        row.add_item(CategorySelect(bot, active=cog_name))
        container.add_item(row)
        self.add_item(container)


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Show all command categories")
    async def help_cmd(self, ctx: commands.Context):
        await ctx.send(view=HelpView(self.bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
