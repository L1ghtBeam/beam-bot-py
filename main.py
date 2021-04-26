import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils import manage_commands

import logging, os, asyncpg


DB_PORT = '5432'

# This is getting too long, make this a json file soon
TOKEN = open('TOKEN.txt', 'r').read()
PG_PASS = open('PG_PASS.txt', 'r').read()
DB_ADDRESS = open('DB_ADDRESS.txt', 'r').read()
DB_NAME = open('DB_NAME.txt', 'r').read()
APPLICATION_ID = open('APPLICATION_ID.txt', 'r').read()

guild_ids = [702716876601688114]


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
    command_prefix = commands.when_mentioned_or('.'),
    help_command = help_command,
    intents=intents,
)
slash = SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True, application_id=APPLICATION_ID)

async def create_db_pool():
    bot.pg_con = await asyncpg.create_pool(host=DB_ADDRESS, port=DB_PORT, database=DB_NAME, user='postgres', password=PG_PASS)

@bot.event
async def on_ready():
    logging.info(f"We have logged in as {bot.user}")

# cogs
@slash.subcommand(
    base = "cogs",
    name = "list",
    description = "Lists the bot's cogs.",
    guild_ids = guild_ids,
)
@commands.is_owner()
async def list(ctx: SlashContext):
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

    await ctx.send(content=content, hidden=True)

@slash.subcommand(
    base = "cogs",
    name = "reload",
    description = "Reload a cog.",
    options = [manage_commands.create_option(
        name = "cog",
        description = "A cog to reload.",
        option_type = 3,
        required = True,
    )],
    guild_ids = guild_ids,
)
@commands.is_owner()
async def reload(ctx: SlashContext, cog: str):
    bot.reload_extension(f"cogs.{cog}")
    await ctx.send(f"Successfully reloaded {cog}.", hidden=True)

@slash.subcommand(
    base = "cogs",
    name = "load",
    description = "Load a cog.",
    options = [manage_commands.create_option(
        name = "cog",
        description = "A cog to load.",
        option_type = 3,
        required = True,
    )],
    guild_ids = guild_ids,
)
@commands.is_owner()
async def load(ctx: SlashContext, cog: str):
    bot.load_extension(f"cogs.{cog}")
    await slash.sync_all_commands()
    await ctx.send(f"Successfully loaded {cog}.", hidden=True)

@slash.subcommand(
    base = "cogs",
    name = "unload",
    description = "Unload a cog.",
    options = [manage_commands.create_option(
        name = "cog",
        description = "A cog to unload.",
        option_type = 3,
        required = True,
    )],
    guild_ids = guild_ids,
)
@commands.is_owner()
async def unload(ctx: SlashContext, cog: str):
    bot.unload_extension(f"cogs.{cog}")
    await slash.sync_all_commands()
    await ctx.send(f"Successfully unloaded {cog}.", hidden=True)

# load cogs
for file in os.listdir('./cogs'):
    if file.endswith('.py') and not file.startswith('_'):
        bot.load_extension(f'cogs.{file[:-3]}')

bot.loop.run_until_complete(create_db_pool())
bot.run(TOKEN)
