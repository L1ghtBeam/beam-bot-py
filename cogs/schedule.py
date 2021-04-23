import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils import manage_commands

import pytz, logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

guild_ids = [834890280959475712]


class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def update_schedule(self, guild_id: str):
        logging.info("Updating guild: {}".format(guild_id))
        db = self.bot.pg_con

        guild = await db.fetchrow("SELECT * FROM guilds WHERE guild_id = $1", guild_id)
        if not guild:
            # guild not found in database
            return
        
        channel = discord.utils.get(self.bot.get_all_channels(), id=int(guild['schedule_channel_id']), guild__id=int(guild_id))
        if not channel:
            # channel not found
            return
        if not channel.permissions_for(channel.guild.me).send_messages:
            # invalid permissions - can't send messages in channel
            return

        message = discord.utils.get(await channel.history(limit=1).flatten(), author=channel.guild.me)
        if not message:
            message = await channel.send("Generating schedule...")
        
        tz = pytz.timezone(guild['timezone'])
        t = datetime.now(tz)

        # event functionality
        events = await db.fetch("SELECT * FROM events WHERE guild_id = $1 ORDER BY timestamp DESC", guild_id)

        # sort events
        sorted_events = [[], [], [], [], [], []]
        for event in events:
            days = (event['timestamp'] - t).days

            # keep inside array
            days = max(0, days)
            days = min(5, days)

            sorted_events[days].append(event)

        def format_events(events, format):
            value = ""
            for event in events:
                value += "{} - {}\n".format(event['timestamp'].strftime(format), event['name'])
            value = value[:-1] if value else "Nothing"
            return value

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            timestamp=datetime.now(pytz.utc),
            title="Schedule for {}".format(t.strftime('%A, %B %d, %Y')),
        )

        embed.set_author(name=channel.guild.name, icon_url=channel.guild.icon_url)

        embed.add_field(name="Today:", value=format_events(sorted_events[0], "%I:%M %p"), inline=False)
        embed.add_field(name="Tomorrow:", value=format_events(sorted_events[1], "%I:%M %p"), inline=False)
        embed.add_field(name=(t+relativedelta(days=+2)).strftime('%A') + ":", value=format_events(sorted_events[2], "%I:%M %p"), inline=False)
        embed.add_field(name=(t+relativedelta(days=+3)).strftime('%A') + ":", value=format_events(sorted_events[3], "%I:%M %p"), inline=False)
        embed.add_field(name=(t+relativedelta(days=+4)).strftime('%A') + ":", value=format_events(sorted_events[4], "%I:%M %p"), inline=False)

        if sorted_events[5]:
            embed.add_field(name="Future:", value=format_events(sorted_events[5], "%m/%d"), inline=False)
        
        embed.set_footer(text=guild['timezone'])
        await message.edit(content=None, embed=embed)

    @cog_ext.cog_subcommand(
        base="schedule",
        name="setup",
        description="Setup the interactive schedule for this server.",
        options=[
            manage_commands.create_option(
                name="channel",
                description="Channel to put the schedule in. Make sure only the bot can send messages in the given channel.",
                option_type=7,
                required=True,
            ),
            manage_commands.create_option(
                name="timezone",
                description="Timezone the schedule will use. A full list can be found with /timezones.",
                option_type=3,
                required=True,
            ),
            manage_commands.create_option(
                name="role",
                description="Role that can manage the schedule. If not included, everyone who can see the schedule can manage it.",
                option_type=8,
                required=False,
            ),
        ],
        guild_ids=guild_ids, # TODO: remove on main
    )
    @commands.guild_only()
    async def setup(self, ctx: SlashContext, channel: discord.TextChannel, timezone: str, role: discord.Role = None):
        guild_id = str(ctx.guild_id)
        db = self.bot.pg_con

        if await db.fetch("SELECT guild_id FROM guilds WHERE guild_id = $1", guild_id):
            await ctx.send("Schedule is already set up for this server!", hidden=True)
            return

        if not timezone in pytz.all_timezones:
            await ctx.send("Invalid timezone! Please refer to /timezones for a list of valid timezones.", hidden=True)
            return

        if not channel.permissions_for(channel.guild.me).send_messages:
            await ctx.send("Invalid permissions! Cannot send messages in {}.".format(channel.mention), hidden=True)
            return
        
        channel_id = str(channel.id)
        if role:
            role_id = str(role.id)
        else:
            role_id = None
        
        await db.execute(
            "INSERT INTO guilds (guild_id, schedule_channel_id, schedule_role_id, timezone, log) VALUES ($1, $2, $3, $4, $5)",
            guild_id, channel_id, role_id, timezone, [f"{ctx.author} created the schedule."]
        )
        await ctx.send("Setup complete!")
        await self.update_schedule(guild_id)

    # function for testing purposes
    @cog_ext.cog_subcommand(
        base="schedule",
        name="update",
        guild_ids=guild_ids, # dont remove
    )
    @commands.guild_only()
    async def update(self, ctx: SlashContext):
        await self.update_schedule(str(ctx.guild_id))
        await ctx.send("Updated schedule!", hidden=True)


def setup(bot):
    bot.add_cog(Schedule(bot))
