import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils import manage_commands

import pytz, logging

guild_ids = [702716876601688114]


class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def update_schedule(self, guild_id: str):
        logging.info("Updating guild: {}".format(guild_id))

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
        db = self.bot.pg_con
        guild_id = str(ctx.guild_id)

        if await db.fetch("SELECT guild_id FROM guilds WHERE guild_id = $1", guild_id):
            await ctx.send("Schedule is already set up for this server!", hidden=True)
            return

        if not timezone in pytz.all_timezones:
            await ctx.send("Invalid timezone! Please refer to /timezones for a list of valid timezones.", hidden=True)
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


def setup(bot):
    bot.add_cog(Schedule(bot))
