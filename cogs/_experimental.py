import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils import manage_commands

import logging

guild_ids = [834890280959475712]


class Experimental(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_subcommand(
        base = "test",
        name = "say",
        description = "Make the bot say something.",
        options = [manage_commands.create_option(
            name = "text",
            description = "What you want the bot to say.",
            option_type = 3,
            required = True
        )],
        guild_ids = guild_ids,
    )
    async def say(self, ctx: SlashContext, text: str):
        await ctx.channel.send(text)

    @cog_ext.cog_subcommand(
        base = "test",
        name = "info",
        description = "Gets information of a member.",
        options = [manage_commands.create_option(
            name = "user",
            description = "User to get information from.",
            option_type = 6,
            required = True
        )],
        guild_ids = guild_ids,
    )
    async def tag(self, ctx: SlashContext, member: discord.Member):
        await ctx.channel.send(f"User joined at {member.joined_at}")

    @cog_ext.cog_subcommand(
        base = "test",
        name = "members",
        description = "Gets all members of a role.",
        options = [manage_commands.create_option(
            name = "role",
            description = "Role to get members from.",
            option_type = 8,
            required = True
        )],
        guild_ids = guild_ids,
    )
    async def role(self, ctx: SlashContext, role: discord.Role):
        for member in role.members:
            await ctx.send(member.name)

def setup(bot):
    bot.add_cog(Experimental(bot))
