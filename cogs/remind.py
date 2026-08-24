import time

import discord
from discord.ext import commands, tasks

from utils import database
from utils import embeds


def parse_duration(raw: str) -> int:
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    raw = raw.strip().lower()
    if raw[-1] in units and raw[:-1].isdigit():
        return int(raw[:-1]) * units[raw[-1]]
    if raw.isdigit():
        return int(raw) * 60
    raise ValueError("Duration must look like 30s, 10m, 2h, or 1d")


class Remind(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_reminders.start()

    def cog_unload(self) -> None:
        self.check_reminders.cancel()

    @commands.hybrid_command(name="remind", description="Set a reminder")
    async def remind(self, ctx: commands.Context, duration: str, *, message: str):
        try:
            seconds = parse_duration(duration)
        except ValueError as exc:
            await ctx.send(view=embeds.error("Invalid Duration", str(exc)), ephemeral=True)
            return
        remind_at = time.time() + seconds
        await database.add_reminder(ctx.guild.id if ctx.guild else 0, ctx.author.id, ctx.channel.id, message, remind_at)
        await ctx.send(view=embeds.success("Reminder Set", f"I'll remind you in {duration}: {message}"), ephemeral=True)

    @commands.hybrid_command(name="reminders", description="List your active reminders")
    async def reminders(self, ctx: commands.Context):
        rows = await database.get_user_reminders(ctx.author.id)
        if not rows:
            await ctx.send(view=embeds.info("No Reminders"), ephemeral=True)
            return
        lines = [f"`#{r['id']}` {r['message']} — <t:{int(r['remind_at'])}:R>" for r in rows]
        await ctx.send(view=embeds.SectionLayout("Your Reminders", lines), ephemeral=True)

    @tasks.loop(seconds=20)
    async def check_reminders(self):
        for reminder in await database.get_due_reminders():
            channel = self.bot.get_channel(reminder["channel_id"])
            await database.complete_reminder(reminder["id"])
            if channel is None:
                continue
            try:
                await channel.send(view=embeds.info("⏰ Reminder", f"<@{reminder['user_id']}> {reminder['message']}"))
            except discord.HTTPException:
                pass

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Remind(bot))
