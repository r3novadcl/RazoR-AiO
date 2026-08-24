import discord
from discord.ext import commands

import config
from utils import database
from utils import embeds
from utils import emojis


class MentionReply(commands.Cog, name="MentionReply"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        bot_user = self.bot.user
        stripped = message.content.strip()
        if stripped not in (f"<@{bot_user.id}>", f"<@!{bot_user.id}>"):
            return

        prefix = database.get_cached_prefix(message.guild.id, config.PREFIX)
        view = embeds.info(
            f"Hey, I'm {config.BOT_NAME} {emojis.get('home', '👋')}",
            f"My prefix here is `{prefix}` — try `{prefix}help` or `/help` to see everything I can do.",
        )
        try:
            await message.reply(view=view, mention_author=False)
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(MentionReply(bot))
