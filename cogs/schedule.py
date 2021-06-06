import discord
from discord.ext import commands, tasks
from discord_slash import cog_ext, SlashContext
from discord_slash.utils import manage_commands

import pytz, logging, os, random, asyncio
from datetime import datetime
from dateutil.relativedelta import relativedelta

guild_ids = [834890280959475712]


class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_all.start()

    def cog_unload(self):
        self.update_all.cancel()

    @tasks.loop(minutes=15.0)
    async def update_all(self):
        guilds = await self.bot.pg_con.fetch("SELECT guild_id from guilds")
        logging.info("Updating guilds...")
        updates = asyncio.gather(*[self.update_schedule(guild['guild_id']) for guild in guilds])
        await updates
        logging.info("Finished updating {} guilds!".format(str(len(guilds))))
    
    @update_all.before_loop
    async def before_update_all(self):
        await self.bot.wait_until_ready()
        logging.info("Starting schedule updater")

    async def fetch_schedule(self, ctx: SlashContext):
        if not ctx.guild:
            # not in a guild
            return None
        
        guild_id = str(ctx.guild.id)
        guild = await self.bot.pg_con.fetchrow("SELECT * FROM guilds WHERE guild_id = $1", guild_id)
        if not guild:
            # schedule is not setup
            return None

        return guild

    async def can_edit_schedule(self, ctx: SlashContext, guild):
        if ctx.guild.owner_id == ctx.author.id:
            # is owner
            return True

        channel = discord.utils.get(self.bot.get_all_channels(), id=int(guild['schedule_channel_id']), guild__id=int(guild['guild_id']))
        if not channel:
            # schedule channel not found
            return False
        
        if channel.permissions_for(ctx.author).administrator:
            # is administrator
            return True

        if not channel.permissions_for(ctx.author).view_channel:
            # cannot view channel
            return False
        
        if guild['schedule_role_id']:
            if not discord.utils.get(ctx.author.roles, id=int(guild['schedule_role_id'])):
                # don't have required role
                return False
        return True

    async def update_schedule(self, guild_id: str):
        db = self.bot.pg_con

        guild = await db.fetchrow("SELECT * FROM guilds WHERE guild_id = $1", guild_id)
        if not guild:
            # guild not found in database
            return
        
        channel = discord.utils.get(self.bot.get_all_channels(), id=int(guild['schedule_channel_id']), guild__id=int(guild_id))
        if not channel:
            # channel not found
            await db.execute("DELETE FROM guilds WHERE guild_id = $1", guild_id)
            return
        if not channel.permissions_for(channel.guild.me).send_messages:
            # invalid permissions - can't send messages in channel
            return

        message = discord.utils.get(await channel.history(limit=1).flatten(), author=channel.guild.me)
        if not message:
            message = await channel.send("Generating schedule...")
        
        tz = pytz.timezone(guild['timezone'])
        now = pytz.utc.localize(datetime.utcnow()).astimezone(tz)

        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # event functionality
        events = await db.fetch("SELECT * FROM events WHERE guild_id = $1 AND timestamp >= $2 ORDER BY timestamp ASC", guild_id, start)

        # sort events
        sorted_events = [[], [], [], [], [], []]
        for event in events:
            days = (event['timestamp'].astimezone(tz).date() - now.date()).days

            if days < 0: # this should never happen anymore but I'm keeping this in just in case
                logging.error(f"Expired event \"{event['id']}\" passed. You shouldn't see this message.")
                continue

            # keep inside array
            days = min(5, days)

            sorted_events[days].append(event)

        def format_events(events, format, tz):
            value = ""
            for event in events:
                t = event['timestamp'].astimezone(tz)
                value += "{} - {}\n".format(t.strftime(format), event['name'])
            value = value[:-1] if value else "Nothing"
            return value

        embed = discord.Embed(
            colour=discord.Colour.blue(),
            timestamp=pytz.utc.localize(datetime.utcnow()),
            title="Schedule for {}".format(now.strftime('%A, %B %d, %Y')),
        )

        embed.set_author(name=channel.guild.name, icon_url=channel.guild.icon_url)

        embed.add_field(name="Today:", value=format_events(sorted_events[0], "%I:%M %p", tz), inline=False)
        embed.add_field(name="Tomorrow:", value=format_events(sorted_events[1], "%I:%M %p", tz), inline=False)
        embed.add_field(name=(now+relativedelta(days=+2)).strftime('%A') + ":", value=format_events(sorted_events[2], "%I:%M %p", tz), inline=False)
        embed.add_field(name=(now+relativedelta(days=+3)).strftime('%A') + ":", value=format_events(sorted_events[3], "%I:%M %p", tz), inline=False)
        embed.add_field(name=(now+relativedelta(days=+4)).strftime('%A') + ":", value=format_events(sorted_events[4], "%I:%M %p", tz), inline=False)

        if sorted_events[5]:
            embed.add_field(name="Future:", value=format_events(sorted_events[5], "%m/%d", tz), inline=False)
        
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
    )
    @commands.guild_only()
    @commands.has_guild_permissions(manage_channels=True)
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

    @cog_ext.cog_subcommand(
        base="schedule",
        subcommand_group="events",
        name="add",
        description="Add an event to the schedule.",
        options=[
            manage_commands.create_option(
                name="name",
                description="Name of the event",
                option_type=3,
                required=True,
            ),
            manage_commands.create_option(
                name="month",
                description="Month of the event.",
                option_type=4,
                required=True,
            ),
            manage_commands.create_option(
                name="day",
                description="Day of the event.",
                option_type=4,
                required=True,
            ),
            manage_commands.create_option(
                name="hour",
                description="Hour of the event.",
                option_type=4,
                required=True,
            ),
            manage_commands.create_option(
                name="minute",
                description="Minute of the event.",
                option_type=4,
                required=True,
            ),
            manage_commands.create_option(
                name="period",
                description="AM or PM.",
                option_type=3,
                required=True,
                choices=[
                    manage_commands.create_choice(
                        value="AM",
                        name="AM",
                    ),
                    manage_commands.create_choice(
                        value="PM",
                        name="PM",
                    ),
                ],
            ),
            manage_commands.create_option(
                name="description",
                description="Description of the event",
                option_type=3,
                required=False,
            ),
            manage_commands.create_option(
                name="timezone",
                description="Your timezone. Will use the server timezone is not specified.",
                option_type=3,
                required=False,
            ),
        ],
    )
    async def event_add(self, ctx:SlashContext, name:str, month:int, day:int, hour:int, minute:int, period:str, description:str = "", timezone:str=""):
        guild = await self.fetch_schedule(ctx)
        if not guild:
            await ctx.send("Schedule not found!", hidden=True)
            return

        if not await self.can_edit_schedule(ctx, guild):
            await ctx.send("You do not have permission to manage this schedule!", hidden=True)
            return

        db = self.bot.pg_con
        PM = period == "PM"

        # checks
        if len(name) > 50:
            await ctx.send("Name too long! Name must not be longer than 50 characters", hidden=True)
            return
        if not 0 <= hour <= 12:
            await ctx.send("Invalid hour!", hidden=True)
            return

        if timezone:
            if timezone not in pytz.all_timezones:
                await ctx.send("Invalid timezone!", hidden=True)
                return
        else:
            timezone = guild['timezone']

        hour = hour % 12 + 12 if PM else hour % 12
        tz = pytz.timezone(timezone)
        now = pytz.utc.localize(datetime.utcnow()).astimezone(tz)
        year = now.year

        try:
            timestamp = tz.localize(datetime(year, month, day, hour, minute))

            if timestamp < now:
                timestamp = tz.localize(datetime(year, month, day, hour, minute))
        except:
            await ctx.send("Invalid time!", hidden=True)
            return

        # generate unused id
        while True:
            id = str(hex(random.randrange(16**6-1)))[2:].zfill(6).upper()
            if not await db.fetch("SELECT id FROM events WHERE id = $1", id):
                break

        await db.execute(
            "INSERT INTO events (id, guild_id, name, description, timestamp) VALUES ($1, $2, $3, $4, $5)",
            id, guild['guild_id'], name, description, timestamp
        )
        await ctx.send("Created new event **{}**.".format(name))
        await self.update_schedule(guild['guild_id'])
        
    @cog_ext.cog_subcommand(
        base="schedule",
        subcommand_group="events",
        name="list",
        description="List events and their IDs.",
        options=[
            manage_commands.create_option(
                name="old_events",
                description="Include events that have ended. False by default.",
                option_type=5,
                required=False,
            ),
        ],
    )
    async def event_list(self, ctx:SlashContext, old_events:bool = False):
        guild = await self.fetch_schedule(ctx)
        if not guild:
            await ctx.send("Schedule not found!", hidden=True)
            return

        if not old_events:
            tz = pytz.timezone(guild['timezone'])
            now = pytz.utc.localize(datetime.utcnow()).astimezone(tz)
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            events = await self.bot.pg_con.fetch("SELECT * FROM events WHERE guild_id = $1 AND timestamp >= $2 ORDER BY timestamp ASC", guild['guild_id'], start)
        else:
            events = await self.bot.pg_con.fetch("SELECT * FROM events WHERE guild_id = $1 ORDER BY timestamp DESC", guild['guild_id'])
        
        content = ""
        for event in events:
            content += f"`{event['id']}` - {event['name']}\n"
        content = content[:-1] if content else "No events found!"
        await ctx.send(content=content, hidden=True)

    @cog_ext.cog_subcommand(
        base="schedule",
        subcommand_group="events",
        name="info",
        description="Get info about an event, including the description",
        options=[
            manage_commands.create_option(
                name="id",
                description="Id of the event get info from. Use /schedule event list to get ids.",
                option_type=3,
                required=True,
            ),
        ],
    )
    async def event_info(self, ctx:SlashContext, id:str):
        db = self.bot.pg_con
        id = id.upper()

        if len(id) != 6:
            await ctx.send("Invalid id! Use `/schedule events list` to get ids.", hidden=True)
            return
        
        event = await db.fetchrow("SELECT * FROM events WHERE id = $1", id)
        if not event:
            await ctx.send("Event not found!", hidden=True)
            return
        
        guild = await self.fetch_schedule(ctx)
        if guild:
            tz = pytz.timezone(guild['timezone'])
        else:
            guild = await self.bot.pg_con.fetchrow("SELECT guild_id, timezone FROM guilds WHERE guild_id = $1", event['guild_id'])
            if guild:
                tz = pytz.timezone(guild['timezone'])
            else:
                tz = pytz.utc

        content = "**{}** - `{}`\n{} ({})".format(event['name'], event['id'], event['timestamp'].astimezone(tz).strftime('%c'), str(tz))

        if event['description']:
            content+=f"\n\n{event['description']}"

        await ctx.send(content=content, hidden=True)

    @cog_ext.cog_subcommand(
        base="schedule",
        subcommand_group="events",
        name="remove",
        description="Remove an event from the schedule.",
        options=[
            manage_commands.create_option(
                name="id",
                description="Id of the event to remove. Use /schedule event list to get ids.",
                option_type=3,
                required=True,
            ),
        ],
    )
    async def event_remove(self, ctx:SlashContext, id:str):
        db = self.bot.pg_con

        if len(id) != 6:
            await ctx.send("Invalid id! Use `/schedule events list` to get ids.", hidden=True)
            return

        guild = await self.fetch_schedule(ctx)
        if not guild:
            await ctx.send("Schedule not found!", hidden=True)
            return

        if not await self.can_edit_schedule(ctx, guild):
            await ctx.send("You do not have permission to manage this schedule!", hidden=True)
            return
        
        event = await db.fetchrow("SELECT id, name FROM events WHERE id = $1 AND guild_id = $2", id, guild['guild_id'])
        if not event:
            await ctx.send("Event not found!", hidden=True)
            return

        await db.execute("DELETE FROM events WHERE id = $1 AND guild_id = $2", event['id'], guild['guild_id'])
        await ctx.send("Deleted event **{}**".format(event['name']))
        await self.update_schedule(guild['guild_id'])

    # function for testing purposes - comment out on master
    @cog_ext.cog_subcommand(
        base="test",
        name="update",
        guild_ids=guild_ids, # dont remove
    )
    @commands.guild_only()
    async def update(self, ctx: SlashContext):
        await self.update_schedule(str(ctx.guild_id))
        await ctx.send("Updated schedule!", hidden=True)

    # function for testing purposes - comment out on master
    @cog_ext.cog_subcommand(
        base="test",
        name="check",
        guild_ids=guild_ids, # dont remove
    )
    async def check_edit(self, ctx: SlashContext):
        guild = await self.fetch_schedule(ctx)
        if not guild:
            await ctx.send("Schedule not found!", hidden=True)
            return
        
        if not await self.can_edit_schedule(ctx, guild):
            await ctx.send("You don't have permission to manage the schedule!", hidden=True)
        else:
            await ctx.send("Can manage the schedule!", hidden=True)


def setup(bot):
    bot.add_cog(Schedule(bot))
