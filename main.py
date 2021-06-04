import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils import manage_commands

import logging, os, asyncpg, json


DB_PORT = '5432'

# get bot data from bot.json file
with open("bot.json", "r") as f:
    bot_data = json.load(f)


# logging
logging.basicConfig(level=logging.INFO)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
logger.addHandler(handler)

logger1 = logging.getLogger()
logger1.setLevel(logging.INFO)
logger1.addHandler(handler)

# intents
intents = discord.Intents.all()
intents.presences = False


help_command = commands.DefaultHelpCommand(
    no_category = 'Other'
)

bot = commands.Bot(
    activity = discord.Activity(type=discord.ActivityType.listening, name='slash commands'),
    command_prefix = commands.when_mentioned,
    help_command = help_command,
    intents=intents,
)
slash = SlashCommand(bot, sync_commands=False, sync_on_cog_reload=False)

async def create_db_pool():
    bot.pg_con = await asyncpg.create_pool(host=bot_data['address'], port=DB_PORT, database=bot_data['name'], user='postgres', password=bot_data['pass'])

@bot.event
async def on_ready():
    logging.info(f"We have logged in as {bot.user}")

# cogs
@bot.command(
    name="cogs",
    aliases=["cog"]
)
@commands.is_owner()
async def cogs(ctx: commands.Context, *args):
    if not args:
        # loaded cogs
        content = "Loaded cogs: "
        for e in bot.extensions.keys():
            content += str(e)[5:] + ", "
        content = content[:-2] + "."

        # all cogs
        content += "\nAll cogs: "
        for f in os.listdir("./cogs"):
            if f == "__pycache__":
                continue
            content += f[:-3] + ", "
        content = content[:-2] + "."

        await ctx.send(content=content)
    elif len(args) > 1:
        if args[0] == "load":
            bot.load_extension(f"cogs.{args[1]}")
            await ctx.send(f"Successfully loaded {args[1]}. Make sure to use the `sync` command!")
        elif args[0] == "unload":
            bot.unload_extension(f"cogs.{args[1]}")
            await ctx.send(f"Successfully unloaded {args[1]}. Make sure to use the `sync` command!")
        elif args[0] == "reload":
            bot.reload_extension(f"cogs.{args[1]}")
            await ctx.send(f"Successfully reloaded {args[1]}. If any commands have been updated, make sure to use the `sync` command!")
        else:
            await ctx.send("Invalid usage!")
    else:
        await ctx.send("Invalid usage!")

@bot.command(
    name="sync"
)
@commands.is_owner()
async def sync(ctx: commands.Context):
    await ctx.send("Syncing commands...")
    await slash.sync_all_commands()
    await ctx.send("Completed syncing all commands!")

# load cogs
for file in os.listdir('./cogs'):
    if file.endswith('.py') and not file.startswith('_'):
        bot.load_extension(f'cogs.{file[:-3]}')

bot.loop.run_until_complete(create_db_pool())
bot.run(bot_data['token'])
