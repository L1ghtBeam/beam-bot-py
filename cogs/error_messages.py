import discord
from discord.ext import commands
from discord_slash import SlashContext

import logging

class Error(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx: SlashContext, ex: Exception):
        # checks.
        if isinstance(ex, commands.errors.NotOwner):
            await ctx.send('Only the bot owner can use this command.')
        elif isinstance(ex, commands.errors.NoPrivateMessage):
            await ctx.send('This command cannot be used in a direct message.')
        # in-command errors.
        elif isinstance(ex, commands.errors.ExtensionNotFound):
            await ctx.send('Extension not found.')
        elif isinstance(ex, commands.errors.ExtensionAlreadyLoaded):
            await ctx.send('Extension already loaded.')
        elif isinstance(ex, commands.errors.ExtensionNotLoaded):
            await ctx.send('Extension not loaded.')
        else:
            logging.exception("Slash command error!", exc_info=ex)

def setup(bot):
    bot.add_cog(Error(bot))
