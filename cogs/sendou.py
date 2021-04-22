import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils import manage_commands

import requests, json, logging, asyncio

with open("data/abilities.json", 'r') as f:
    data = f.read()
abilitiesDict = json.loads(data)

with open("data/modes.json", 'r') as f:
    data = f.read()
modesDict = json.loads(data)


class Sendou(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def get_weapon_alias(self, weapon: str):
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

    def list_abilities(self, abilities):
        out = ''
        for i in range(len(abilities)):
            a = abilitiesDict[abilities[i]]
            if i == 0:
                out += a + "   "
            else:
                out += a
        out = out
        return out

    def build_not_found(self):
        return "Builds not found! Make sure the weapon is spelled correctly with proper capitalization and/or the user has a sendou.ink account. Weapons must match **exactly** to how they are found in the game.\nExamples: `Splattershot Jr.`, `Neo Splash-o-matic`, `N-ZAP '85`."

    @cog_ext.cog_slash(
        name = "builds",
        description = "Gets builds for a specific weapon.",
        options = [
            manage_commands.create_option(
                name = "weapon",
                description = "A weapon from Splatoon 2. Use proper capitalization.",
                option_type = 3,
                required = False,
            ),
            manage_commands.create_option(
                name = "user",
                description = "A user to get builds from.",
                option_type = 6,
                required = False,
            ),
        ],
    )
    @commands.guild_only()
    async def builds(self, ctx: SlashContext, weapon: str = "", user: discord.User = None):
        if not weapon and not user:
            await ctx.send("Please include a weapon and/or a user.")
            return

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

        weapon = self.get_weapon_alias(weapon) if weapon else weapon

        if user:
            p = {'discordId': user_id}
            r = requests.get("https://sendou.ink/api/bot/builds", params=p)
            d = r.json()
        else:
            d = []
            for w in weapon:
                p = {'weapon': w}
                r = requests.get("https://sendou.ink/api/bot/builds", params=p)
                d.extend(r.json())

        if not d:
            await ctx.send(self.build_not_found())
            return

        d = sorted(d, key = lambda i: (i['top500'], i['updatedAt']), reverse=True)

        data = []
        if weapon and user:
            for b in d:
                if b['weapon'] in weapon:
                    data.append(b)
        else:
            data = d

        if not data:
            await ctx.send(self.build_not_found())
            return

        message = await ctx.send("Getting builds...")
        index = 0
        while True:
            build = data[index]

            title = "Builds"
            if weapon:
                title += " for " + weapon[0]
            if user:
                title += " by " + user_name

            embed = discord.Embed(
                colour = colour,
                timestamp=ctx.message.created_at,
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

            value = self.list_abilities(build['headAbilities'])
            value += "\n" + self.list_abilities(build['clothingAbilities'])
            value += "\n" + self.list_abilities(build['shoesAbilities'])

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
            await message.edit(content=None, embed=embed)

            for e in ["⏮️", "◀️", "▶️"]:
                await message.add_reaction(e)

            def check(reaction: discord.Reaction, user: discord.User):
                return user == ctx.author and (str(reaction.emoji) in ["⏮️", "◀️", "▶️"]) and reaction.message.id == message.id

            try:
                reaction, react_user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await message.clear_reactions()
                break
            else:
                reactionStr = str(reaction)
                if reactionStr == "⏮️":
                    index = 0
                elif reactionStr == "◀️":
                    index -= 1
                elif reactionStr == "▶️":
                    index += 1

                index = max(index, 0)
                index = min(index, len(data) - 1)
                await reaction.remove(react_user)


def setup(bot):
    bot.add_cog(Sendou(bot))
