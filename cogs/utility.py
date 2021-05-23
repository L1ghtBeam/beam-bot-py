import discord
from discord import guild
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils import manage_commands


class Utility(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name = "ping",
        description = "Returns the bot's latency.",
    )
    async def ping(self, ctx: SlashContext):
        await ctx.send(f"Pong! ({round(self.bot.latency * 1000)}ms)")

    @cog_ext.cog_slash(
        name = "timezones",
        description = "Gets a list of timezones.",
    )
    async def timezones(self, ctx: SlashContext):
        if ctx.guild_id is None:
            with open("data/timezones.txt", "rb") as file:
                await ctx.send(file=discord.File(file, "timezones.txt"))
        else:
            await ctx.send(content="Check your DM!", hidden=True)
            channel = await ctx.author.create_dm()
            with open("data/timezones.txt", "rb") as file:
                await channel.send(file=discord.File(file, "timezones.txt"))
    
    @cog_ext.cog_subcommand(
        base="help",
        name="schedule",
        description="Get help for schedule commands and setup.",
    )
    async def help_schedule(self, ctx:SlashContext):
        content = open("data/help/schedule.txt", "r").read()
        await ctx.send(content=content, hidden=True)


def setup(bot):
    bot.add_cog(Utility(bot))
