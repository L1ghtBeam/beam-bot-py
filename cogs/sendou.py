from asyncio.tasks import wait_for
import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.context import ComponentContext
from discord_slash.utils.manage_commands import create_option
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle

import aiohttp, json, logging, asyncio
from datetime import datetime

with open("data/abilities.json", 'r') as f:
    data = f.read()
abilitiesDict = json.loads(data)

with open("data/modes.json", 'r') as f:
    data = f.read()
modesDict = json.loads(data)


class Sendou(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name = "builds",
        description = "Gets builds for a specific weapon.",
        options = [
            create_option(
                name = "weapon",
                description = "A weapon from Splatoon 2. Use proper capitalization.",
                option_type = 3,
                required = False,
            ),
            create_option(
                name = "user",
                description = "A user to get builds from.",
                option_type = 6,
                required = False,
            ),
        ],
    )
    async def builds(self, ctx: SlashContext, weapon: str = "", user: discord.User = None):
        if not weapon and not user:
            await ctx.send("Please include a weapon and/or a user.")
            return
        await ctx.defer()

        def build_not_found():
            return "Builds not found! Make sure the weapon is spelled correctly with proper capitalization and/or the user has a sendou.ink account. Weapons must match **exactly** to how they are found in the game.\nExamples: `Splattershot Jr.`, `Neo Splash-o-matic`, `N-ZAP '85`."

        def get_weapon_alias(weapon: str):
            alias = (
                ("Tentatek Splattershot", "Octo Shot Replica"),
                ("Splattershot", "Hero Shot Replica"),
                ("Blaster", "Hero Blaster Replica"),
                ("Splat Roller", "Hero Roller Replica"),
                ("Octobrush", "Herobrush Replica"),
                ("Splat Charger", "Hero Charger Replica"),
                ("Slosher", "Hero Slosher Replica"),
                ("Heavy Splatling", "Hero Splatling Replica"),
                ("Splat Dualies", "Hero Dualie Replicas"),
                ("Splat Brella", "Hero Brella Replica")
            )
            for a in alias:
                if weapon in a:
                    return a
            return (weapon,)

        def list_abilities(abilities):
            out = ''
            for i in range(len(abilities)):
                a = abilitiesDict[abilities[i]]
                if i == 0:
                    out += a + "   "
                else:
                    out += a
            out = out
            return out

        def create_components(button1, button2, button3):
                buttons = [
                    create_button(
                        style=ButtonStyle.gray,
                        emoji="⏮️",
                        disabled=button1,
                        custom_id="first",
                    ),
                    create_button(
                        style=ButtonStyle.grey,
                        emoji="◀️",
                        disabled=button2,
                        custom_id="back",
                    ),
                    create_button(
                        style=ButtonStyle.grey,
                        emoji="▶️",
                        disabled=button3,
                        custom_id="forward",
                    )
                ]
                action_row = create_actionrow(*buttons)
                return [action_row]

        if user and type(user) in (discord.User, discord.Member):
            user_id = user.id
            user_name = user.name
            colour = user.color
        elif user:
            user_id = user
            user_name = f"ID: `{user}`"
            colour = discord.Color.blue()
        else:
            colour = discord.Color.blue()

        weapon = get_weapon_alias(weapon) if weapon else weapon

        async with aiohttp.ClientSession() as session:
            if user:
                params = {'discordId': user_id}
                async with session.get("https://sendou.ink/api/bot/builds", params=params) as resp:
                    raw_data = await resp.json()
            else:
                raw_data = []
                for w in weapon:
                    params = {'weapon': w}
                    async with session.get("https://sendou.ink/api/bot/builds", params=params) as resp:
                        raw_data.extend(await resp.json())

        if not raw_data:
            await ctx.send(build_not_found())
            return

        raw_data = sorted(raw_data, key = lambda i: (i['top500'], i['updatedAt']), reverse=True)

        data = []
        if weapon and user:
            for build in raw_data:
                if build['weapon'] in weapon:
                    data.append(build)
        else:
            data = raw_data

        if not data:
            await ctx.send(build_not_found())
            return

        index = 0
        button_ctx = None
        while True:
            build = data[index]

            title = "Builds"
            if weapon:
                title += " for " + weapon[0]
            if user:
                title += " by " + user_name

            embed = discord.Embed(
                colour = colour,
                timestamp=datetime.utcnow(),
                title=title,
                description = f"Build {index + 1}/{len(data)}"
            )

            weaponStr = build['weapon'].replace(" ", "%20")
            weaponStr = weaponStr.replace(".", "")
            embed.set_thumbnail(url=f"https://sendou.ink/_next/image?url=%2Fweapons%2F{weaponStr}.png&w=256&q=75")

            if build['title']:
                name = build['title']
            else:
                name = 'No title'

            value = f"Build by {build['user']['username']}"
            if build['top500']:
                value += ' <:top_500:818372865266810902>'

            embed.add_field(name=name, value=value, inline=False)

            value = list_abilities(build['headAbilities'])
            value += "\n" + list_abilities(build['clothingAbilities'])
            value += "\n" + list_abilities(build['shoesAbilities'])

            embed.add_field(name="Abilities:", value=value)
            
            value = ""
            for m in build['modes']:
                value += modesDict[m]
            value = "No modes." if not value else value

            embed.add_field(name="Modes:", value=value)

            value = build['description'] if build['description'] else "No description."
            embed.add_field(name="Description:", value=value, inline=False)

            primaryOnly = [
                "AD",
                "CB",
                "DR",
                "H",
                "LDE",
                "NS",
                "OG",
                "OS",
                "RP",
                "SJ",
                "T",
                "TI",
            ]
            abilities = ""
            primaries= ""
            for a in build['abilityPoints']:
                if a in primaryOnly:
                    primaries += abilitiesDict[a]
                else:
                    abilities += abilitiesDict[a] + ": " + str(build['abilityPoints'][a]) + "\n"
            abilities = abilities[:-1]
            value = primaries + "\n" + abilities

            embed.add_field(name="Ability Points:", value=value, inline=False)

            embed.set_footer(text="Powered by sendou.ink")

            first_page = index == 0
            last_page = index == len(data) - 1

            components = create_components(first_page, first_page, last_page)

            if button_ctx is None:
                msg = await ctx.send(content=None, embed=embed, components=components)
            else:
                await button_ctx.edit_origin(content=None, embed=embed, components=components)

            # def check(button_ctx: ComponentContext):
            #     return button_ctx.author_id == ctx.author_id

            while True:
                try:
                    button_ctx = await wait_for_component(self.bot, messages=msg, timeout=60.0)
                except asyncio.TimeoutError:
                    components = create_components(True, True, True)
                    await msg.edit(content=None, embed=embed, components=components)
                    return
                else:
                    if button_ctx.author_id == ctx.author_id:
                        if button_ctx.custom_id == "first":
                            index = 0
                        elif button_ctx.custom_id == "back":
                            index -= 1
                        elif button_ctx.custom_id == "forward":
                            index += 1
                        
                        index = max(index, 0)
                        index = min(index, len(data) - 1)
                        break
                    else:
                        asyncio.create_task(
                            button_ctx.send("You cannot interact with this message.", hidden=True)
                        )

    @builds.error
    async def builds_error(self, ctx, error):
        logging.exception("Builds error!", exc_info=error)
        await ctx.send("An error occurred!")


def setup(bot):
    bot.add_cog(Sendou(bot))
