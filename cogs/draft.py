import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils import manage_commands

import asyncio, logging, random, datetime, pytz, math
import time as t

guild_ids = [702716876601688114]


class Draft(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="draft",
        description="Randomizes teams for a draft.",
        options=[
            manage_commands.create_option(
                name="time",
                description="Amount of seconds that the draft is available to join. Default is 30.",
                option_type=4,
                required=False,
            ),
        ],
    )
    @commands.guild_only()
    async def draft(self, ctx: SlashContext, time = 30):
        embed = discord.Embed(
            colour=discord.Colour.blue(),
            timestamp=discord.utils.snowflake_time(int(ctx.interaction_id)),
            title="React with ☑️ to join the draft.",
            description=f"Draft closes in {time} seconds.",
        )

        message = await ctx.send(embed=embed)
        await message.add_reaction("☑️")

        start_time = t.time()

        while t.time() < start_time + time:
            await asyncio.sleep(1)
            embed.description=f"Draft closes in {math.ceil(start_time + time - t.time())} seconds."
            await message.edit(embed=embed)
    
        message = await message.channel.fetch_message(message.id)

        reaction = None
        for reaction in message.reactions:
            if str(reaction.emoji) == "☑️":
                break
        users = await reaction.users().flatten()

        users.remove(self.bot.user)

        random.shuffle(users)

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            timestamp=datetime.datetime.now(pytz.utc),
            title="Draft teams.",
        )

        team_count = 0
        while len(users) >= 4:
            team_count += 1
            value = ""
            for i in range(4):
                value += str(users[0]) + "\n"
                del users[0]
            value = value[:-1]
            embed.add_field(name=f"Team {team_count}:", value=value)
        
        if len(users) > 0:
            value = ""
            for user in users:
                value += str(user) + "\n"
            value = value[:-1]
            embed.add_field(name=f"Extra players:", value=value)

        embed.description=f"Generated {team_count} teams with {len(users)} players left over."

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Draft(bot))
