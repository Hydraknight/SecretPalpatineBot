import asyncio
import random
import dotenv
import discord
from discord import app_commands
from discord.ui import Button, View, Select
from discord.ext import commands, tasks
import pickle
import os
import json
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


# Set up the bot
intents = discord.Intents.all()
intents.message_content = True  # Required to read messages
intents.dm_messages = True  # Enable direct messaging

bot = commands.Bot(command_prefix='!', intents=intents)

# File to store game state
GAME_STATE_FILE = 'game_state.pkl'

# Load game state from file if it exists


def load_game_state():
    if os.path.exists(GAME_STATE_FILE):
        with open(GAME_STATE_FILE, 'rb') as f:
            return pickle.load(f)
    return {}

# Save game state to file


def save_game_state():
    with open(GAME_STATE_FILE, 'wb') as f:
        pickle.dump(game_sessions, f)


def load_stats():
    if os.path.exists('stats_xl.json'):
        with open('stats_xl.json', 'r') as f:
            return json.load(f)
    return {}


def save_stats():
    global stats
    with open('stats_xl.json', 'w') as f:
        json.dump(stats, f, indent=4)


async def initialize_player_stats(player_id):
    global stats
    if player_id not in stats:
        stats[player_id] = {
            'wins': 0,
            'losses': 0,
            'games': 0,
            'win_as_Fascist': 0,
            'win_as_Liberal': 0,
            'win_as_Hitler': 0,
            'win_as_Anarchist': 0,
            'win_as_Capitalist': 0,
            'win_as_Monarchist': 0,
            'win_as_Communist': 0,
            'loss_as_Fascist': 0,
            'loss_as_Liberal': 0,
            'loss_as_Hitler': 0,
            'loss_as_Anarchist': 0,
            'loss_as_Capitalist': 0,
            'loss_as_Monarchist': 0,
            'loss_as_Communist': 0,
            'policies_enacted': {'Liberal': 0, 'Fascist': 0, 'Communist': 0, 'Anarchist': 0, 'Anti Fascist': 0, 'Anti Communist': 0},
            'times_chancellor': 0,
            'successful_votes': 0,
            'failed_votes': 0,
        }


user_cache = {}


async def get_user_cached(user_id):
    """Fetch a user from the cache or Discord API if not cached."""
    if user_id in user_cache:
        return user_cache[user_id]

    user = await bot.fetch_user(user_id)
    user_cache[user_id] = user
    return user


@bot.event
async def on_ready():
    global game_sessions, session, channel, stats
    print(f'We have logged in as {bot.user.display_name}')
    await bot.tree.sync()
    game_sessions = load_game_state()
    stats = load_stats()
    # if game sessions is not empty:
    global user_cache
    # Cache all members on startup
    for guild in bot.guilds:
        for member in guild.members:
            user_cache[member.id] = member
    if game_sessions != {}:
        session = game_sessions[list(game_sessions.keys())[0]]
        if session.get('channel_id', False):
            channel = await bot.fetch_channel(session['channel_id'])


@bot.event
async def on_message(message):
    # Check if the message is a direct message
    global game_sessions
    if game_sessions != {}:
        session = game_sessions[list(game_sessions.keys())[0]]
    else:
        session = False
    if session and session.get('communism', False):
        if isinstance(message.channel, discord.DMChannel):
            # Get the user who sent the message
            user_id = message.author.id
            # Ensure the bot doesn't process its own messages
            if user_id != bot.user.id:
                # Check if the user is a Communist
                if session['roles'][user_id] == 'Communist':
                    communists = [
                        player for player, role in session['roles'].items() if role == 'Communist']

                    # Forward the message to all Communists
                    for communist_id in communists:
                        if communist_id != user_id:  # Don't send the message back to the sender
                            communist_user = await get_user_cached(communist_id)
                            await communist_user.send(f"<@{user_id}>: {message.content}")

    # Allow the bot to process other commands
    await bot.process_commands(message)


@bot.hybrid_command(name="next_president", description="Go to the next president")
async def next_president(ctx: commands.Context):
    global user_cache
    guild_id = ctx.guild.id
    session = game_sessions.get(guild_id)
    # admin check:
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="Permission Denied",
            description="You do not have permission to go the next president.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    # Get the current president and chancellor
    president_id = session['president']
    # Get the list of players
    players = session['players']
    # Find the index of the current president
    president_index = players.index(president_id)
    # Calculate the index of the next player
    next_president_index = (president_index + 1) % len(players)
    # Set the next player as the new president
    session['president'] = players[next_president_index]
    save_game_state()
    # Notify the players
    new_president = user_cache[session['president']]
    await ctx.send(f"The next President is {new_president.mention}!")
    # Start the next election round
    session['state'] = 'new_round'
    await start_election_round(ctx, session, channel)

# command to start next round:@


@bot.hybrid_command(name="roleinfo", description="Gives information abour the role")
@app_commands.describe(role="The role to get information about")
@app_commands.choices(role=[app_commands.Choice(name='Liberal', value='Liberal'), app_commands.Choice(name='Fascist', value='Fascist'), app_commands.Choice(name='Hitler', value='Hitler'), app_commands.Choice(name='Communist', value='Communist'), app_commands.Choice(name='Capitalist', value='Capitalist'), app_commands.Choice(name='Anarchist', value='Anarchist'), app_commands.Choice(name='Monarchist', value='Monarchist')])
async def roleinfo(ctx: commands.Context, role: str):
    if role not in ['Liberal', 'Fascist', 'Hitler', 'Communist', 'Capitalist', 'Monarchist', 'Anarchist']:
        await ctx.send("Invalid role", ephemeral=True)
        return
    await ctx.defer()
    if role == 'Liberal':
        color = discord.Color.blue()
        desc = f"🟦 **You are a Liberal.** 🟦\n# GOAL\nYour mission is to safeguard the future of the country by enacting five Liberal Policies or by uncovering and eliminating Hitler\n\n## Strategy\nStay alert and trust your instincts. The Fascists will attempt to manipulate and deceive the government for their own gain. While you must rely on your fellow Liberals, remain cautious—anyone could be hiding their true allegiance. Protect democracy at all costs, but tread carefully—your enemies are cunning. 🕵️‍♂️\n"
    elif role == 'Hitler':
        color = discord.Color.orange()
        desc = f"🟧 **You are Hitler.** 🟧\n# GOAL\nAlthough you are aligned with the Fascists, your survival depends on maintaining the guise of a Liberal. Only the Fascists know your true identity\n\n## Strategy\nWork subtly with your Fascist allies to advance their agenda without revealing yourself. Victory is achieved if you are elected Chancellor after three Fascist Policies have been enacted. But beware—if the Liberals discover your identity, they will stop at nothing to bring about your downfall. 🎭\n"

    elif role == 'Fascist':
        color = discord.Color.yellow()
        desc = f"🟨 **You are a Fascist.** 🟨\n# GOAL\nYour mission is to subvert the Liberal government and secure power for Hitler. Work behind the scenes to sow discord and enact six Fascist Policies\n\n## Strategy\nAvoid detection while working to ensure that Hitler becomes Chancellor after three Fascist Policies are enacted. Manipulate, deceive, and undermine the Liberals at every turn. 🕵️\n\n\n"

    elif role == 'Communist':
        color = discord.Color.red()
        desc = f"🟥 **You are a Communist.** 🟥\n# GOAL\nThe Communists have two potential paths to victory\n\n1. **Policy Victory:** Fill the Communist policy tracker with Communist policies. 📜\n2. **Assassination Victory:** Assassinate Hitler, allowing the Communists to win alongside the Liberals. \n\n## Strategy\nWork covertly to advance Communist policies or identify and eliminate Hitler. Victory is within reach through strategic alliances and careful planning. \n\n"
    elif role == 'Capitalist':
        color = discord.Color.gold()
        desc = f"🟨 **You are a Capitalist.** 🟨\n# GOAL\nThe Capitalist has a singular win condition\n\n**Victory is yours if neither the Anarchist nor the Communists achieve their goals.** \n\n## Strategy\nWork to prevent the rise of both the Anarchists and the Communists. Maintain the status quo to ensure that your interests remain protected in the new regime. 🏛️\n"
    elif role == 'Anarchist':
        color = discord.Color.dark_grey()
        desc = f"⚫ **You are an Anarchist.** ⚫\n# GOAL\n### Win Condition\n- **Victory Condition:** The Anarchist wins if the Communists win and two of the policies on the Communist tracker are Anarchist policies. 🏴\n- **Additional Condition:** The Anarchist wins if Hitler is assassinated. \n\n## Strategy\nNavigate the chaos to ensure that your policies are enacted, and align yourself with the right forces to topple the existing order. 🌀\n\n# Special Power:\nAfter a policy is enacted, you have the option to kill a player in the game, but at the same time, you must reveal your identity. **This power can be used only once!** 🔫\nTo use this power, use the command `/reveal` before the President ends their term.\n"
    elif role == 'Monarchist':
        color = discord.Color.purple()
        desc = f"🟪 **You are a Monarchist.** 🟪\n# GOAL\nThe Monarchist dreams of returning to the imperial past and holds reservations about Hitler's leadership\n\n## Victory Condition:\n- The Monarchist wins if the Fascists win and Hitler never becomes Chancellor after three Fascist policies are enacted. 🏰\n- The Monarchist loses if Hitler is assassinated. \n\n## Strategy\nYour goal is to both protect Hitler and ensure that he never ascends to power. Play a delicate game of intrigue, where your survival depends on the balance of power. 🎯\n"

    embed = discord.Embed(
        title=f"Your Role: **{role}**",
        description=desc,
        color=color
    )
    card = f"GameAssets/{role} Card.png"
    if os.path.isfile(card):
        file = discord.File(card, filename="card.png")
        embed.set_image(url="attachment://card.png")
        await ctx.send(embed=embed, file=file)


@bot.tree.command(name="next_round", description="Start the next round of the game")
async def next_round(ctx: commands.Context):
    global user_cache
    guild_id = ctx.guild.id
    session = game_sessions.get(guild_id)
    if not session:
        embed = discord.Embed(
            title="No Game Session Available",
            description="There is no game session available to start the next round.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if session['state'] != 'new_round':
        embed = discord.Embed(
            title="Invalid Command",
            description="You can only start the next round when the current round has ended.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    await start_election_round(ctx, session, channel)


class PaginatedEmbed(View):
    def __init__(self, embeds, timeout=180):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0

        # Ensure each button has a unique custom_id
        self.prev_button = Button(emoji="◀️", style=discord.ButtonStyle.primary, custom_id="prev_page")
        self.next_button = Button(emoji='▶️', style=discord.ButtonStyle.primary, custom_id="next_page")

        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page

        self.add_item(self.prev_button)
        self.add_item(self.next_button)

    async def start(self, ctx):
        self.message = await ctx.send(embed=self.embeds[self.current_page], view=self)

    async def prev_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self.message.edit(embed=self.embeds[self.current_page])

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            await self.message.edit(embed=self.embeds[self.current_page])


@bot.hybrid_command(name="player_stats", description="Shows the stats of a player")
async def player_stats(ctx: commands.Context, player: discord.Member = None):
    if player is None:
        player = ctx.author

    player_id = str(player.id)
    if player_id not in stats:
        await initialize_player_stats(player_id)
        save_stats()

    # Embed 1: General Stats
    embed1 = discord.Embed(
        title=f"Player Stats: {player.display_name} - General",
        color=discord.Color.blue()
    )
    embed1.add_field(name="🏅 **Overall Stats**", value=f"**`Matches:`** {stats[player_id]['games']}\n**`Wins:`** {stats[player_id]['wins']}\n**`Losses:`** {stats[player_id]['losses']}\n**`Win Rate:`** {
                     round(((stats[player_id]['wins'] / 1) if stats[player_id]['games'] == 0 else stats[player_id]['wins']/stats[player_id]['games']) * 100, 2)}%\n", inline=False)
    embed1.add_field(name="📜 **Policies Enacted**", value=f"**Liberal:** {stats[player_id]['policies_enacted']['Liberal']}\n**Fascist:** {stats[player_id]['policies_enacted']['Fascist']}\n**Communist:** {
                     stats[player_id]['policies_enacted']['Communist']}\n**Anarchist:** {stats[player_id]['policies_enacted']['Anarchist']}", inline=False)
    embed1.add_field(name="👔 **Leadership Roles**", value=f"**Times as Chancellor:** {stats[player_id]['times_chancellor']}", inline=False)
    embed1.add_field(name="🗳️ **Voting Stats**", value=f"**✅Successful Votes:** {
                     stats[player_id]['successful_votes']}\n**❌Failed Votes:** {stats[player_id]['failed_votes']}", inline=False)
    embed1.set_thumbnail(url=player.avatar)
    embed1.set_footer(text=f"Stats for {
                      player.display_name}", icon_url=player.avatar)

    # Embed 2: XL Role Stats
    embed2 = discord.Embed(
        title=f"Player Stats: {player.display_name} - XL Roles",
        color=discord.Color.green()
    )
    embed2.add_field(name="🟦 **As Liberal**", value=f"➠ **`Wins:`** {
                     stats[player_id]['win_as_Liberal']}\n➠ **`Losses:`** {stats[player_id]['loss_as_Liberal']}\n", inline=True)
    embed2.add_field(name="🟧 **As Fascist**", value=f"➠ **`Wins:`** {
                     stats[player_id]['win_as_Fascist']}\n➠ **`Losses:`** {stats[player_id]['loss_as_Fascist']}\n", inline=True)
    embed2.add_field(name="🔴 **As Hitler**", value=f"➠ **`Wins:`** {
                     stats[player_id]['win_as_Hitler']}\n➠ **`Losses:`** {stats[player_id]['loss_as_Hitler']}\n", inline=True)
    embed2.add_field(name="🟥 **As Communist**", value=f"➠ **`Wins:`** {
                     stats[player_id]['win_as_Communist']}\n➠ **`Losses:`** {stats[player_id]['loss_as_Communist']}\n", inline=True)
    embed2.add_field(name="🟨 **As Capitalist**", value=f"➠ **`Wins:`** {
                     stats[player_id]['win_as_Capitalist']}\n➠ **`Losses:`** {stats[player_id]['loss_as_Capitalist']}\n", inline=True)
    embed2.add_field(name="⚫ **As Anarchist**", value=f"➠ **`Wins:`** {
                     stats[player_id]['win_as_Anarchist']}\n➠ **`Losses:`** {stats[player_id]['loss_as_Anarchist']}\n", inline=True)
    embed2.add_field(name="🟪 **As Monarchist**", value=f"➠ **`Wins:`** {
                     stats[player_id]['win_as_Monarchist']}\n➠ **`Losses:`** {stats[player_id]['loss_as_Monarchist']}\n", inline=True)
    embed2.set_thumbnail(url=player.avatar)
    embed2.set_footer(text=f"Stats for {
                      player.display_name}", icon_url=player.avatar)

    # Paginated Embed
    embeds = [embed1, embed2]
    paginated_view = PaginatedEmbed(embeds)
    await paginated_view.start(ctx)


@bot.hybrid_command(name="start_game", description="Start a new Secret Hitler game session")
async def start_game(ctx: commands.Context):
    global game_sessions
    guild_id = ctx.guild.id

    if guild_id in game_sessions:
        embed = discord.Embed(
            title="Game Already in Progress",
            description="A game is already in progress in this server. Please wait for it to finish or use `!terminate_game` to terminate the current session.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Initialize the game session
    game_sessions[guild_id] = {
        'players': [ctx.author.id],
        'roles': {},
        'state': 'waiting',
        'running': False,
        'queue': [],
        'mode': 'Normal'
    }
    await initialize_player_stats(str(ctx.author.id))
    save_game_state()

    embed = discord.Embed(
        title="New Game Session Started",
        description="A new game session has been started! Players can join using `!join_game`.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# Hybrid command to stop the current game session


@bot.hybrid_command(name="set_mode", description="Set the game mode")
@app_commands.describe(mode="Sets the mode")
@app_commands.choices(mode=[app_commands.Choice(name='XL', value='XL'), app_commands.Choice(name='Normal', value='Normal'),])
async def set_mode(ctx: commands.Context, mode: str):
    guild_id = ctx.guild.id
    session = game_sessions.get(guild_id)
    if not session:
        embed = discord.Embed(
            title="No Game Session Available",
            description="There is no game session available to set the mode.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    session['mode'] = mode
    save_game_state()
    embed = discord.Embed(
        title="Mode Set",
        description=f"Game mode has been set to **{mode}**.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)


@bot.hybrid_command(name="stop_game", description="Stop the game")
async def stop_game(ctx: commands.Context):
    # Check if the user is an admin
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="Permission Denied",
            description="You do not have permission to stop the game.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return

    guild_id = ctx.guild.id
    session = game_sessions.get(guild_id)
    if not session:
        embed = discord.Embed(
            title="No Game Session Available",
            description="There is no game session available to stop.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if session and not session['running']:
        embed = discord.Embed(
            title="Game stopped",
            description="Game has been stopped and lobby has been cleared.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        del game_sessions[guild_id]
        save_game_state()
        return
# Hybrid command for players to join the game
# command to set the current session state to new_round:


@bot.hybrid_command(name="new_round", description="Join the Secret Hitler game")
async def new_round(ctx: commands.Context):
    # admin check:
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="Permission Denied",
            description="You do not have permission to start the new round.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    guild_id = ctx.guild.id
    session = game_sessions[guild_id]
    session['state'] = 'new_round'
    channel = await bot.fetch_channel(session['channel_id'])
    save_game_state()
    # await start_election_round(ctx, session, channel)


@bot.hybrid_command(name="join_game", description="Join the Secret Hitler game")
async def join_game(ctx: commands.Context):
    global stats
    guild_id = ctx.guild.id
    session = game_sessions.get(guild_id, None)
    if not session:
        embed = discord.Embed(
            title="No Game Session Available",
            description="There is no game session available to join.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if session and session['running']:
        # If the game is running, add the player to the queue
        player = ctx.author
        if player.id in session['queue']:
            embed = discord.Embed(
                title="Already in Queue",
                description="You are already in the queue for the next game.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            session['queue'].append(player.id)
            save_game_state()
            embed = discord.Embed(
                title="Added to Queue",
                description=f"**{
                    player.display_name}** has been added to the queue for the next game!",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=player.avatar)
            await ctx.send(embed=embed)
        return

    # Normal join process
    player = ctx.author
    if player.id in session['players']:
        embed = discord.Embed(
            title="Already Joined",
            description="You have already joined the game.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    session['players'].append(player.id)
    await initialize_player_stats(str(player.id))
    save_game_state()

    embed = discord.Embed(
        title="Player Joined",
        description=f"**{player.display_name}** has joined the game!",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=player.avatar)
    await ctx.send(embed=embed)


# command to leave lobby:


@bot.hybrid_command(name="leave_game", description="Leave the Secret Hitler game")
async def leave_game(ctx: commands.Context):
    guild_id = ctx.guild.id
    player_id = ctx.author.id
    if guild_id not in game_sessions or game_sessions[guild_id]['state'] != 'waiting':
        embed = discord.Embed(
            title="No Game Session Available",
            description="There is no game session available to leave.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if player_id not in game_sessions[guild_id]['players']:
        embed = discord.Embed(
            title="Not Joined",
            description="You have not joined the game.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    game_sessions[guild_id]['players'].remove(player_id)
    save_game_state()
    player = ctx.author
    embed = discord.Embed(
        title="Player Left",
        description=f"**{player.display_name}** has left the game.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# kick players:


@bot.hybrid_command(name="kick_player", description="Kick a player from the game")
async def kick_player(ctx: commands.Context, player: discord.Member):
    # admin check:
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="Permission Denied",
            description="You do not have permission to kick players from the game.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    guild_id = ctx.guild.id
    player_id = player.id
    if guild_id not in game_sessions or game_sessions[guild_id]['state'] != 'waiting':
        embed = discord.Embed(
            title="No Game Session Available",
            description="There is no game session available to kick players from.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    if player_id not in game_sessions[guild_id]['players']:
        embed = discord.Embed(
            title="Player Not Joined",
            description="The player you are trying to kick has not joined the game.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    game_sessions[guild_id]['players'].remove(player_id)
    save_game_state()
    embed = discord.Embed(
        title="Player Kicked",
        description=f"**{player.display_name}** has been kicked from the game.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)


@bot.hybrid_command(name="lobby", description="Current game lobby")
async def lobby(ctx: commands.Context):
    if ctx:
        guild_id = ctx.guild.id
        await ctx.defer()
    else:
        guild_id = list(game_sessions.keys())[0]
        session = game_sessions(guild_id)
    if not game_sessions.get(guild_id, False):
        embed = discord.Embed(
            title="No Game Session Available",
            description="There is no game session available to view the lobby.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    players = game_sessions[guild_id]['players']
    if not players:
        embed = discord.Embed(
            title="No Players",
            description="No players have joined the game yet.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

        return
    player_list = ""
    for i, player in enumerate(players):
        player_list += f"{i+1}. **<@{player}>**" + "\n"

    embed = discord.Embed(
        title="Current Game Lobby",
        description=f"Players in the lobby:\n{player_list}",
        color=discord.Color.blue()
    )
    if ctx:
        await ctx.send(embed=embed)
    else:
        initchannel = await bot.fetch_channel(session['initchannel'])
        await initchannel.send(embed=embed)

# Hybrid command to start the game once all players have joined


@bot.hybrid_command(name="begin_game", description="Begin the Secret Hitler game")
async def begin_game(ctx: commands.Context):
    # check if user is admin:
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="Permission Denied",
            description="You do not have permission to start the game.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    global session, channel, user_cache
    await ctx.defer()
    guild = ctx.guild
    guild_id = guild.id
    session = game_sessions.get(guild_id)
    session['guild_id'] = guild_id
    session['init_channel'] = ctx.channel.id
    session['running'] = True
    session['enacted_policies'] = []
    session['election_tracker'] = 0
    session['discard_pile'] = []
    session['last_government'] = {
        'president': None,
        'chancellor': None
    }
    player_count = len(session['players'])
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        guild.me: discord.PermissionOverwrite(
            read_messages=True, send_messages=True)
    }
    if session['mode'] == 'Normal':
        POLICIES = ['Liberal'] * 6 + ['Fascist'] * 11
        random.shuffle(POLICIES)

        session['policies'] = POLICIES
        if not session or session['state'] != 'waiting':
            embed = discord.Embed(
                title="No Game Ready to Begin",
                description="There is no game session ready to begin. Please start a game with `!start_game`.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if player_count < 1:
            embed = discord.Embed(
                title="Not Enough Players",
                description="Not enough players to start the game. A minimum of 5 players is required.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        if session['state'] == 'starting':
            embed = discord.Embed(
                title="Game Already Starting",
                description="The game is already starting.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        session['state'] = 'starting'
        save_game_state()
        # Role Assignment
        fascists_count = max(1, (player_count // 3))
        if player_count == 6:
            fascists_count = 1
        liberals_count = player_count - fascists_count - 1
        roles = ['Liberal'] * liberals_count + \
            ['Fascist'] * fascists_count + ['Hitler']

        random.shuffle(session['players'])
        session['roles'] = {session['players'][i]: roles[i]
                            for i in range(player_count)}
        random.shuffle(session['players'])
        # get the list of fascists in session['players']:
        fascists = [user_cache[player] for player in session['players'] if session['roles'][player]
                    == 'Fascist']
        fascists = [fascist.display_name for fascist in fascists]
        other_fascists = ""
        if len(session['players']) <= 6:
            other_fascists = f"\n## Fascists:\n **{', '.join(fascists)}**"

        hitler = None
        for player in session['players']:
            if session['roles'][player] == 'Hitler':
                hitler = user_cache[player]
                break

        # First player starts as President

        # all the participants should be able to view and type in the channel"
        for player_id in session['players']:
            player = user_cache[player_id]
            # dm the rhe role as an embed:
            role = session['roles'][player_id]
            if role == 'Liberal':
                color = discord.Color.blue()
                desc = f"You are a **Liberal**.\n# GOAL\n Your goal is to protect the future of the country by enacting five Liberal Policies or by finding and killing Hitler. Stay vigilant, as the Fascists will try to deceive and manipulate the government for their nefarious purposes. Trust your instincts and your fellow Liberals, but be cautious—anyone could be a hidden Fascist or, worse, Hitler."
            elif role == 'Hitler':
                color = discord.Color.red()
                desc = f"You are **Hitler**.\n# GOAL\n Although you are part of the Fascist team, you must act like a Liberal to avoid suspicion. Your identity is known only to the Fascists. Work with them subtly to advance Fascist policies without revealing yourself. Victory is yours if you are elected Chancellor after three Fascist Policies have been enacted. Be careful—if the Liberals discover your identity, they will stop at nothing to assassinate you.{
                    other_fascists}"
            else:
                color = discord.Color.orange()
                desc = f"You are a **Fascist**.\n# GOAL\n Your mission is to undermine the Liberal government and pave the way for Hitler to rise to power. Work in secret to sow discord and enact six Fascist Policies. Be careful, as you must avoid detection. Your ultimate goal is to ensure Hitler's election as Chancellor after three Fascist Policies have been enacted.\n## Fascists:\n **{', '.join(fascists)}**\n## Hitler:\n**{
                    hitler.display_name if hitler else 'No Hitler'}**"
            embed = discord.Embed(
                title=f"Your Role: **{role}**",
                description=desc,
                color=color
            )
            card = f"GameAssets/{role} Card.png"
            if os.path.isfile(card):
                file = discord.File(card, filename="card.png")
                embed.set_image(url="attachment://card.png")
                await player.send(embed=embed, file=file)

            overwrites[player] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True)
    elif session['mode'] == 'XL':
        fascists_count = max(1, ((player_count-3) // 3))
        communists_count = max(1, (player_count // 4))
        capitalist_count = 1 if player_count > 10 else 0
        anarchist_count = 1 if player_count > 9 else 0
        monarchist_count = 1 if player_count > 12 else 0
        liberals_count = player_count - fascists_count - communists_count - \
            capitalist_count - anarchist_count - monarchist_count - 1
        roles = ['Liberal'] * liberals_count + \
                ['Fascist'] * fascists_count + \
                ['Hitler'] + \
                ['Communist'] * communists_count + \
                ['Capitalist'] * capitalist_count + \
                ['Anarchist'] * anarchist_count + \
                ['Monarchist'] * monarchist_count
        if player_count <= 9:
            POLICIES = ['Communist']*8 + ['Liberal'] * 6 + ['Fascist'] * 9
        else:
            POLICIES = ['Anti Fascist'] + ['Anti Communist'] + ['Communist'] * \
                7 + ['Liberal'] * 6 + ['Fascist'] * 9 + ['Anarchist']*2
        random.shuffle(POLICIES)
        session['policies'] = POLICIES
        random.shuffle(session['players'])
        session['roles'] = {session['players'][i]: roles[i]
                            for i in range(player_count)}
        random.shuffle(session['players'])
        session['anarchy_execution'] = False
        session['vonc'] = True
        random.shuffle(session['players'])
        fascists = [user_cache[player] for player in session['players'] if session['roles'][player]
                    == 'Fascist']
        fascists = [fascist.display_name for fascist in fascists]
        anarchist_player = ""
        for player_id in session['players']:
            if session['roles'][player_id] == 'Anarchist':
                anarchist_player = f"Anarchist: <@{player_id}>"
        other_fascists = ""
        if len(session['players']) <= 6:
            other_fascists = f"\n## Fascists:\n **{', '.join(fascists)}**"

        hitler = None
        for player in session['players']:
            if session['roles'][player] == 'Hitler':
                hitler = user_cache[player]
                break
        for player_id in session['players']:
            player = user_cache[player_id]
            # dm the role as an embed:
            role = session['roles'][player_id]
            if role == 'Liberal':
                color = discord.Color.blue()
                desc = f"🟦 **You are a Liberal.** 🟦\n# GOAL\nYour mission is to safeguard the future of the country by enacting five Liberal Policies or by uncovering and eliminating Hitler\n\n## Strategy\nStay alert and trust your instincts. The Fascists will attempt to manipulate and deceive the government for their own gain. While you must rely on your fellow Liberals, remain cautious—anyone could be hiding their true allegiance. Protect democracy at all costs, but tread carefully—your enemies are cunning. 🕵️‍♂️\n"
            elif role == 'Hitler':
                color = discord.Color.orange()
                desc = f"🟧 **You are Hitler.** 🟧\n# GOAL\nAlthough you are aligned with the Fascists, your survival depends on maintaining the guise of a Liberal. Only the Fascists know your true identity\n\n## Strategy\nWork subtly with your Fascist allies to advance their agenda without revealing yourself. Victory is achieved if you are elected Chancellor after three Fascist Policies have been enacted. But beware—if the Liberals discover your identity, they will stop at nothing to bring about your downfall. 🎭\n"

            elif role == 'Fascist':
                color = discord.Color.yellow()
                desc = f"🟨 **You are a Fascist.** 🟨\n# GOAL\nYour mission is to subvert the Liberal government and secure power for Hitler. Work behind the scenes to sow discord and enact six Fascist Policies\n\n## Strategy\nAvoid detection while working to ensure that Hitler becomes Chancellor after three Fascist Policies are enacted. Manipulate, deceive, and undermine the Liberals at every turn. 🕵️\n\n## Fascist Allies:\n**{', '.join(fascists)}*\n\n## Hitler:\n**{
                    hitler.display_name if hitler else 'No Hitler'}**\n"

            elif role == 'Communist':
                color = discord.Color.red()
                desc = f"🟥 **You are a Communist.** 🟥\n# GOAL\nThe Communists have two potential paths to victory\n\n1. **Policy Victory:** Fill the Communist policy tracker with Communist policies. 📜\n2. **Assassination Victory:** Assassinate Hitler, allowing the Communists to win alongside the Liberals. \n\n## Strategy\nWork covertly to advance Communist policies or identify and eliminate Hitler. Victory is within reach through strategic alliances and careful planning. \n\n## Comrades:\n**{', '.join([
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           f'<@{comm}>' for comm in session['players'] if session['roles'][comm] == 'Communist'])}\n{anarchist_player}**\n"
            elif role == 'Capitalist':
                color = discord.Color.gold()
                desc = f"🟨 **You are a Capitalist.** 🟨\n# GOAL\nThe Capitalist has a singular win condition\n\n**Victory is yours if neither the Anarchist nor the Communists achieve their goals.** \n\n## Strategy\nWork to prevent the rise of both the Anarchists and the Communists. Maintain the status quo to ensure that your interests remain protected in the new regime. 🏛️\n"
            elif role == 'Anarchist':
                color = discord.Color.dark_grey()
                desc = f"⚫ **You are an Anarchist.** ⚫\n# GOAL\n### Win Condition\n- **Victory Condition:** The Anarchist wins if the Communists win and two of the policies on the Communist tracker are Anarchist policies. 🏴\n- **Additional Condition:** The Anarchist wins if Hitler is assassinated. \n\n## Strategy\nNavigate the chaos to ensure that your policies are enacted, and align yourself with the right forces to topple the existing order. 🌀\n\n# Special Power:\nAfter a policy is enacted, you have the option to kill a player in the game, but at the same time, you must reveal your identity. **This power can be used only once!** 🔫\nTo use this power, use the command `/reveal` before the President ends their term.\n"
            elif role == 'Monarchist':
                color = discord.Color.purple()
                desc = f"🟪 **You are a Monarchist.** 🟪\n# GOAL\nThe Monarchist dreams of returning to the imperial past and holds reservations about Hitler's leadership\n\n## Victory Condition:\n- The Monarchist wins if the Fascists win and Hitler never becomes Chancellor after three Fascist policies are enacted. 🏰\n- The Monarchist loses if Hitler is assassinated. \n\n## Strategy\nYour goal is to both protect Hitler and ensure that he never ascends to power. Play a delicate game of intrigue, where your survival depends on the balance of power. 🎯\n"

            embed = discord.Embed(
                title=f"Your Role: **{role}**",
                description=desc,
                color=color
            )
            card = f"GameAssets/{role} Card.png"
            if os.path.isfile(card):
                file = discord.File(card, filename="card.png")
                embed.set_image(url="attachment://card.png")
                await player.send(embed=embed, file=file)

            overwrites[player] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True)
    channel = await guild.create_text_channel('secret-Hitler', overwrites=overwrites)
    session['channel_id'] = channel.id

    chl = await bot.fetch_channel(channel.id)
    # beatiful embed that game is starting at channel:
    embed = discord.Embed(
        title="Game Starting",
        description=f"Game starting! Head over to {
            chl.mention} to play Secret Hitler!"
    )
    img = "GameAssets/Banner.png"
    if os.path.isfile(img):
        file = discord.File(img, filename="banner.png")
        embed.set_image(url="attachment://banner.png")
        await ctx.send(embed=embed, file=file)
    order = ''
    for i, mention in enumerate(session['players']):
        order += f"{i+1}. <@{mention}>\n"
    message = await channel.send(f"Game has started! Players in order:\n {order}")
    await message.pin()
    # Announce the first President
    president = session['players'][0]
    session['president'] = president
    # await channel.send(f"The first President is {president.mention}!")
    save_game_state()
    # Start the first election round
    await start_election_round(ctx, session, channel)


class ChancellorSelect(Select):
    def __init__(self, ctx, players):
        self.ctx = ctx
        self.selected_chancellor_id = None  # Store the selected chancellor's ID
        options = [discord.SelectOption(
            label=user.display_name, value=str(user.id)) for user in players]
        super().__init__(placeholder="Select a Chancellor...",
                         min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Store the selected chancellor's ID but don't proceed yet
        global user_cache
        self.selected_chancellor_id = int(self.values[0])
        selected_chancellor = user_cache[self.selected_chancellor_id]
        await interaction.response.send_message(
            f"You have selected {selected_chancellor.mention}. Please click 'Lock In' to confirm.", ephemeral=True)


@bot.hybrid_command(name="reveal", description="Reveal that you are an anarchist and execute a player")
@app_commands.describe(player="The player to execute")
async def reveal(ctx: commands.Context, player: discord.Member):
    global user_cache
    guild_id = ctx.guild.id
    session = game_sessions.get(guild_id)
    channel = await bot.fetch_channel(session['channel_id'])
    if not session:
        embed = discord.Embed(
            title="No Game Session Available",
            description="There is no game session available to reveal as an anarchist.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    if session['state'] != 'new_round':
        embed = discord.Embed(
            title="Invalid Command",
            description="You can only reveal as an anarchist during the new round phase.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    if session['mode'] != 'XL':
        embed = discord.Embed(
            title="Invalid Command",
            description="You can only reveal as an anarchist during the XL mode.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    if ctx.author.id not in session['players']:
        embed = discord.Embed(
            title="Not Joined",
            description="You have not joined the game.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    if session['roles'][ctx.author.id] != 'Anarchist':
        embed = discord.Embed(
            title="Invalid Command",
            description="You can only reveal as an anarchist.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    if player.id not in session['players']:
        embed = discord.Embed(
            title="Invalid Player",
            description="The player you are trying to execute is not in the game.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    if player.id == ctx.author.id:
        embed = discord.Embed(
            title="Invalid Player",
            description="You cannot execute yourself.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return
    if session['anarchy_execution']:
        embed = discord.Embed(
            title="Invalid Command",
            description="You have already executed a player this round.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)
        return

    # Initial suspense message
    await ctx.send("Revealing...", ephemeral=True)
    players = session['players']
    president_killed = False
    if player.id == session['president']:
        current_president_index = players.index(session['president'])
        next_president_index = (current_president_index + 1) % len(players)
        session['president'] = players[next_president_index]
        president_killed = True
    e = discord.Embed(
        title="???????",
        description="Whats happening?",
        color=0x000000
    )
    session['state'] = 'execution'
    message = await channel.send(embed=e)
    # Dramatic reveal sequence
    suspense_embeds = [
        discord.Embed(title="The Anarchist makes their move...",
                      description="A decision has been made.", color=discord.Color.dark_red()),
        discord.Embed(title="A figure steps forward...",
                      description="Silence falls over the room...", color=discord.Color.dark_red()),
        discord.Embed(title="The tension is palpable...", description=f"{
                      player.display_name} looks around nervously...", color=discord.Color.dark_red())
    ]

    for embed in suspense_embeds:
        await asyncio.sleep(2)
        await message.edit(embed=embed)

    # Final reveal of the murdered player and Anarchist
    final_embed = discord.Embed(
        title="An Execution Takes Place!",
        description=f"{
            player.mention} has been **executed** by the Anarchist!",
        color=discord.Color.red()
    )
    final_embed.add_field(name="But that's not all...",
                          value="The Anarchist now reveals their true identity!")
    # Optional: add an image for dramatic effect
    anarchist_image = "GameAssets/Anarchist Win.png"
    if os.path.isfile(anarchist_image):
        file = discord.File(anarchist_image, filename="AnarchistWin.png")
        final_embed.set_image(url="attachment://AnarchistWin.png")
        await asyncio.sleep(3)
        await message.delete()
        message = await message.channel.send(embed=final_embed, file=file)

    # Reveal the Anarchist
    anarchist_reveal_embed = discord.Embed(
        title="Anarchist Revealed!",
        description=f"The Anarchist is none other than **{
            ctx.author.display_name}**!",
        color=0x000000
    )
    # Optional: add an image for the Anarchist
    anarchist_reveal_embed.set_thumbnail(
        url=ctx.author.avatar)

    if os.path.isfile(anarchist_image):
        file = discord.File(anarchist_image, filename="AnarchistWin.png")
        anarchist_reveal_embed.set_image(url="attachment://AnarchistWin.png")
        await asyncio.sleep(3)
        await message.channel.send(embed=anarchist_reveal_embed, file=file)
    session['executed_players'] = session.get(
        'executed_players', [])
    session['executed_players'].append(player.id)
    session['players'].remove(player.id)
    # Check if the executed player is Hitler
    if await check_win(ctx, session, channel, player.id, ctx.author.id):
        await channel.send("The executed player was not Hitler. The game continues.")
        if session['roles'][player.id] == 'Capitalist':
            session['policies'].extend(['Communist'])
            random.shuffle(session['policies'])
        # Adjust permissions for the executed player
        await channel.set_permissions(player, send_messages=False, add_reactions=False, read_messages=True)
        if player.id in session.get('last_government', {}).values():
            # set that value as none:
            if player.id == session["last_government"]["president"]:
                session["last_government"]["president"] = None
            else:
                session["last_government"]["chancellor"] = None
        # Mark the execution as used
        session['anarchy_execution'] = True
        save_game_state()
        session['state'] = 'new_round'
        session['pressed_button'] = False
        president = user_cache[session['president']]
        view = PropagandaView(ctx, session['policies'], session, channel)
        if not session.get('propaganda', False) and not president_killed:
            await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

        await asyncio.sleep(5)
        if await check_win(ctx, session, channel):
            # handle the case where the president was executed:
            if president_killed:
                embed = discord.Embed(
                    title="End of Term",
                    description=f"Since the president was shot dead.. We move to the next president by hierarchy.",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)
                await asyncio.sleep(5)
                await start_election_round(ctx, session, channel)
            elif session['state'] == 'new_round' and not session.get('pressed_button', False):
                embed = discord.Embed(
                    title="End of Term",
                    description=f"President {
                        president.mention}, your term is ending. Click the button below to proceed.",
                    color=discord.Color.blue()
                )

                # Add the button to end the term
                view = EndTermView(session, ctx, channel)
                await channel.send(embed=embed, view=view)
                save_game_state()


class LockInButton(discord.ui.Button):
    def __init__(self, label="Lock In"):
        super().__init__(label=label, style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if isinstance(view, ChancellorSelectView):
            await view.lock_in_chancellor_selection(interaction)
            await interaction.followup.edit_message(message_id=interaction.message.id, content="Your Chancellor choice is **locked in**.")
        if isinstance(view, EnactPolicyView):
            await view.lock_in_policy_enactment(interaction)
            await interaction.followup.edit_message(message_id=interaction.message.id, content="The policy to be enacted is **locked in**.")
        if isinstance(view, DiscardPolicyView):
            await view.lock_in_policy_discard(interaction)
            await interaction.followup.edit_message(message_id=interaction.message.id, content="The policy to be discarded is **locked in**.")
        if isinstance(view, InvestigateLoyaltyView):
            await view.lock_in_investigation(interaction)
            await interaction.followup.edit_message(message_id=interaction.message.id, content="The choice for investigation is **locked in**.")
        if isinstance(view, SpecialElectionView):
            await view.lock_in_special_election(interaction)
            await interaction.followup.edit_message(message_id=interaction.message.id, content="The player choice for the new president is **locked in**.")
        if isinstance(view, ExecutionView):
            await view.lock_in_execution(interaction)
            await interaction.followup.edit_message(message_id=interaction.message.id, content="The player to be executed is **locked in**.")
        if isinstance(view, BuggingView):
            await view.lock_in_bugging(interaction)
            await interaction.followup.edit_message(message_id=interaction.message.id, content="The player to be bugged is **locked in**.")
        if isinstance(view, RadicalizationView):
            await view.lock_in_radicalization(interaction)
            await interaction.followup.edit_message(message_id=interaction.message.id, content="The player to be radicalized is **locked in**.")


class ChancellorSelectView(View):
    def __init__(self, ctx, players):
        super().__init__()
        self.ctx = ctx
        self.select = ChancellorSelect(ctx, players)
        self.add_item(self.select)
        self.add_item(LockInButton())

    async def lock_in_chancellor_selection(self, interaction: discord.Interaction):
        global user_cache
        chancellor_id = self.select.selected_chancellor_id
        if not chancellor_id:
            await interaction.response.send_message("Please select a Chancellor first.", ephemeral=True)
            return

        global game_sessions
        # first item in the game_sessions dictionary:
        session = game_sessions[list(game_sessions.keys())[0]]
        session['chancellor'] = chancellor_id
        save_game_state()

        chancellor = user_cache[chancellor_id]
        channel = await bot.fetch_channel(session['channel_id'])
        # await interaction.response.defer()
        await interaction.response.send_message(f"You have chosen a Chancellor. Return to {channel.mention}")
        await channel.send(f"{interaction.user.mention} has chosen {chancellor.mention} as the Chancellor. Proceeding to the vote.")

        # Disable all items in the view after locking in the selection
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        # Start the vote process
        await start_vote(self.ctx, session['channel_id'], interaction.user, chancellor)


@bot.hybrid_command(name="nominate_chancellor", description="Resend the Chancellor selection message in case the previous one timed out.")
async def resend_chancellor(ctx: discord.Interaction):
    # Ensure this command can only be used when the state is in chancellor_nomination
    guild_id = ctx.guild.id
    session = game_sessions.get(guild_id)

    if session['state'] != 'chancellor_nomination':
        await ctx.send("This command can only be used during the Chancellor nomination phase.", ephemeral=True)
        return

    channel = await bot.fetch_channel(session['channel_id'])
    await start_election_round(ctx, session, channel)
    await ctx.send("Chancellor selection message has been resent.", ephemeral=True)


async def start_election_round(ctx, session, channel):
    # Fetch the guild using the stored guild_id
    global user_cache
    guild = bot.get_guild(session['guild_id'])
    if guild is None:
        # Handle the case where the guild cannot be found
        await channel.send("Error: Guild not found.")
        return

    president_id = session['president']
    last_gov = session.get('last_government', None)
    if last_gov:
        last_chancellor = last_gov.get('chancellor', None)
        last_president = last_gov.get('president', None)
    else:
        last_chancellor = None
        last_president = None
    if len(session['players']) < 5:
        invalid = [president_id, last_chancellor]
    else:
        invalid = [last_chancellor, last_president, president_id]
    # invalid = []
    players = []
    for member in guild.members:  # Use the fetched guild object
        if member.id in session['players'] and member.id not in invalid:
            players.append(member)

    # Announce the start of the election round
    embed = discord.Embed(
        title="Election Phase",
        description=f"<@{president_id}> is now the Presidential Candidate. Please choose a Chancellor in your DM.",
        color=discord.Color.blue()
    )
    # set president avatar as thumbnail:
    president = user_cache[president_id]
    embed.set_thumbnail(url=president.avatar)
    president_image_path = "GameAssets/President.png"
    if os.path.isfile(president_image_path):
        file = discord.File(president_image_path, filename="president.png")
        embed.set_image(url="attachment://president.png")
        await channel.send(embed=embed, file=file)

    # Create and send the dropdown
    view = ChancellorSelectView(ctx, players)
    await president.send(f"{president.mention}, please nominate a Chancellor by selecting from the dropdown below:", view=view)
    session['state'] = 'chancellor_nomination'
    save_game_state()


async def start_vote(ctx, channel_id, president, chancellor):
    global user_cache
    channel = bot.get_channel(channel_id)
    if not channel:
        return
    embed = discord.Embed(
        title="Vote on the Government",
        description=f"{president.mention} has nominated {
            chancellor.mention} as Chancellor. Please vote!",
        color=discord.Color.green()
    )
    session['chancellor_candidate'] = chancellor.id
    embed.set_thumbnail(url=chancellor.avatar)
    ja_nein = "GameAssets/Votes.png"
    if os.path.isfile(ja_nein):
        file = discord.File(ja_nein, filename="janein.png")
        embed.set_image(url="attachment://janein.png")
        vote_status = ""
        for player_id in session['players']:
            player = user_cache[player_id]
            vote_status += f"{player.display_name}: ❓ (Not Voted)\n"
        vote_embed = discord.Embed(
            title="Current Voting Status",
            description=vote_status,
            color=discord.Color.blue()
        )
        vote_message = await channel.send(embed=vote_embed)
        view = ChancellorVoteView(
            vote_message, session, session['players'], ctx)
        await channel.send(embed=embed, view=view, file=file)

async def check_win(ctx, session, channel, executed_player=None, assassin=None):
    fasc_count = sum(
        1 for p in session['enacted_policies'] if p == 'Fascist')
    lib_count = sum(1 for p in session['enacted_policies'] if p == 'Liberal')
    comm_count = sum(
        1 for p in session['enacted_policies'] if p == 'Communist')
    anar_count = sum(
        1 for p in session['enacted_policies'] if p == 'Anarchist')
    state = session['state']
    roles = session['roles']
    if state == 'legislative_session':
        candidate = session.get('chancellor_candidate', "")
        if roles[candidate] == 'Hitler' and fasc_count >= 3:
            await channel.send("The Chancellor was Hitler! The Fascists win!")
            session['state'] = 'game_end'
            await terminate_game(None, ["Fascist", "Capitalist"])
            return 0
    elif executed_player:
        if roles[executed_player] == 'Hitler':
            await channel.send("The executed player was Hitler! The Liberals win!")
            session['state'] = 'game_end'
            await terminate_game(None, ["Liberal", "Communist", "Anarchist"])
            return 0
        if roles[executed_player] == 'Capitalist':
            if roles.get(assassin, None) in ['Communist', 'Anarchist']:
                await channel.send("The Capitalist was executed! Communists and Anarchists Win!")
                session['state'] = 'game_end'
                await terminate_game(None, ['Communist', 'Anarchist'])
                return 0
    else:
        if fasc_count >= 6:
            await channel.send("The Fascists have enacted six policies. Fascists Win!")
            session['state'] = 'game_end'
            await terminate_game(None, ['Fascist', "Capitalist", "Monarchist"])
            return 0
        elif lib_count >= 5:
            await channel.send("The Liberals have enacted five policies! The Liberals win!")
            session['state'] = 'game_end'
            await terminate_game(None, ["Liberal", "Capitalist"])
            return 0
        elif anar_count >= 2:
            await channel.send("The Anarchists have enacted two policies! The Anarchists win!")
            session['state'] = 'game_end'
            await terminate_game(None, ["Anarchist"])
            return 0
        elif comm_count + anar_count >= 6:
            await channel.send("The Communists have enacted six policies! The Communists win!")
            session['state'] = 'game_end'
            await terminate_game(None, ["Communist"])
            return 0

    save_game_state()
    return 1


class ChancellorVoteView(View):
    def __init__(self, vote_message, session, players, ctx):
        super().__init__()
        self.players = players
        self.votes = {}  # Dictionary to store votes, format: {user_id: vote}
        self.ctx = ctx
        self.session = session
        self.vote_message = vote_message  # Store the message object for vote updates
        self.vote_evaluated = False  # Flag to prevent duplicate evaluations
        embed = discord.Embed(
            title="Vote for the Government",
            description="Please vote on the proposed government.",
            color=discord.Color.blue()
        )
        asyncio
        asyncio.create_task(self.auto_evaluate_votes())

    @discord.ui.button(label="Ja!", style=discord.ButtonStyle.green)
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_vote(interaction.user.id, True, interaction)

    @discord.ui.button(label="Nein", style=discord.ButtonStyle.red)
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_vote(interaction.user.id, False, interaction)

    async def handle_vote(self, user_id, vote, interaction):
        if user_id not in session['players']:
            await interaction.response.send_message("You are not a player in the game!", ephemeral=True)
            return
        if user_id in self.votes:
            await interaction.response.send_message("You have already voted!", ephemeral=True)
            return

        # Record the user's vote
        self.votes[user_id] = vote
        await interaction.response.send_message(f"You voted {'Yes' if vote else 'No'}!", ephemeral=True)

        # Update vote status message
        await self.update_vote_status(interaction)

        if len(self.votes) == len(self.players) and not self.vote_evaluated:
            self.vote_evaluated = True  # Set the flag to prevent duplicate evaluation
            await self.evaluate_votes()

    async def update_vote_status(self, interaction):
        global user_cache
        vote_status = ""
        for player_id in self.players:
            player = user_cache[player_id]

            if player_id in self.votes:
                vote_status += f"{player.display_name}: ✅ Voted\n"
            else:
                vote_status += f"{player.display_name}: ❓ (Not Voted)\n"

        embed = discord.Embed(
            title="Current Voting Status",
            description=vote_status,
            color=discord.Color.blue()
        )

        if self.vote_message is None:
            # Send the initial vote status message and store the message object
            self.vote_message = await interaction.channel.send(embed=embed)
        else:
            # Edit the existing message with the updated vote status
            await self.vote_message.edit(embed=embed)

    async def evaluate_votes(self):
        global user_cache
        yes_votes = sum(1 for vote in self.votes.values() if vote)
        no_votes = len(self.votes) - yes_votes

        # Show final voting breakdown
        final_vote_status = ""
        for player_id, vote in self.votes.items():
            player = user_cache[player_id]
            final_vote_status += f"{player.display_name}: {
                '✅ Yes' if vote else '❌ No'}\n"

        final_message = f"Final Vote Count:\n\n{
            final_vote_status}\nTotal Yes: {yes_votes}\nTotal No: {no_votes}"

        # Update the vote message with the final results
        embed = discord.Embed(
            title="Final Voting Results",
            description=final_message,
            color=discord.Color.green() if yes_votes > no_votes else discord.Color.red()
        )

        channel = await bot.fetch_channel(self.session['channel_id'])
        await channel.send(embed=embed)
        if yes_votes > no_votes:
            # Government is elected
            self.session['state'] = 'legislative_session'
            self.session['election_tracker'] = 0
            if await check_win(self.ctx, self.session, self.session['channel_id']):
                president = self.session['president']
                candidate = session.get('chancellor_candidate', "")
                global stats
                stats[candidate]['times_chancellor'] += 1
                stats[candidate]['successful_votes'] += yes_votes
                stats[candidate]['failed_votes'] += no_votes
                message = f"# The new chancellor is <@{candidate}>!!\n\n## Proceeding to the legislative session.\n\n-# <@{
                    president}>, please discard a policy in your DM."
                embed = discord.Embed(
                    title="The Government has been Elected.",
                    description=message,
                    color=discord.Color.green()
                )
                chancellor_image_path = "GameAssets/Chancellor.png"
                if os.path.isfile(chancellor_image_path):
                    file = discord.File(
                        chancellor_image_path, filename="chancellor.png")
                    embed.set_image(url="attachment://chancellor.png")
                    await channel.send(embed=embed, file=file)

                # Proceed to the legislative session
                await legislative_session(self.ctx, self.session, channel)
        else:
            # Election fails, advance the election tracker
            await self.handle_failed_election()

    async def auto_evaluate_votes(self):
        # Wait for 90 seconds
        await asyncio.sleep(90)

        # Check if the votes have not been evaluated yet
        if not self.vote_evaluated:
            self.vote_evaluated = True  # Set the flag to prevent duplicate evaluation
            await self.evaluate_votes()

    async def handle_failed_election(self):
        self.session['election_tracker'] += 1
        channel = await bot.fetch_channel(self.session['channel_id'])
        await channel.send(f"The election has failed. The Election Tracker is now at {self.session['election_tracker']}.")

        # Show the updated election tracker image
        lib_count = sum(
            1 for p in self.session['enacted_policies'] if p == 'Liberal')
        lib_tracker = f"GameAssets/Liberal Tracker {
            self.session['election_tracker']}-{lib_count}.png"
        if os.path.isfile(lib_tracker):
            file = discord.File(lib_tracker, filename="libtracker.png")
            await channel.send(file=file)
        # update last government:

        if self.session['election_tracker'] >= 3:
            # Chaos occurs: enact the top policy
            await self.enact_top_policy_due_to_chaos(channel)
        else:
            # Start the next election round
            await self.start_next_election()

    async def enact_top_policy_due_to_chaos(self, channel):
        # Enact the top policy automatically due to chaos
        global user_cache
        if len(self.session.get('policies', [])) == 0:
            # If the policy deck is empty, shuffle the discard pile back into the policy deck
            self.session.get('policies', []).extend(
                self.session.get('discard_pile', []))
            self.session['discard_pile'] = []
            random.shuffle(self.session.get('policies', []))

        top_policy = self.session.get('policies', []).pop(0)
        self.session['enacted_policies'].append(top_policy)
        self.session['election_tracker'] = 0  # Reset the Election Tracker

        await channel.send(f"Three elections have failed. The country is in chaos, and the top policy has been enacted.")
        if top_policy == 'Fascist':
            color = discord.Color.red()
        else:
            color = discord.Color.blue()
        embed = discord.Embed(
            title="Policy Enacted",
            description=f"The top policy was... **{top_policy}**!! .",
            color=color
        )
        policy_card = f"GameAssets/{top_policy} Article.png"
        if os.path.isfile(policy_card):
            file = discord.File(policy_card, filename="policy.png")
            embed.set_image(url="attachment://policy.png")
            await channel.send(embed=embed, file=file)
        self.session['state'] = 'new_round'
        self.session['pressed_button'] = False
        president = user_cache[self.session['president']]
        view = PropagandaView(
            self.ctx, self.session['policies'], self.session, self.channel)
        if session.get('mode', 'Normal') == 'XL' and not session.get('propaganda', False):
            await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

        await asyncio.sleep(10)
        if await check_win(self.ctx, self.session, self.channel):
            if self.session['state'] == 'new_round' and not self.session.get('pressed_button', False):
                embed = discord.Embed(
                    title="End of Term",
                    description=f"President {
                        president.mention}, your term is ending. Click the button below to proceed.",
                    color=discord.Color.blue()
                )

                # Add the button to end the term
                view = EndTermView(session, self.ctx, channel)
                await channel.send(embed=embed, view=view)
                save_game_state()

    async def start_next_election(self):
        global user_cache
        self.session['state'] = 'new_round'
        self.session['pressed_button'] = False
        president = user_cache[self.session['president']]
        view = PropagandaView(
            self.ctx, self.session['policies'], self.session, self.session['channel'])
        if session.get('mode', 'Normal') == 'XL' and not session.get('propaganda', False):
            await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

        await asyncio.sleep(10)
        if self.session['state'] == 'new_round' and not self.session.get('pressed_button', False):
            embed = discord.Embed(
                title="End of Term",
                description=f"President {
                    president.mention}, your term is ending. Click the button below to proceed.",
                color=discord.Color.blue()
            )

            # Add the button to end the term
            view = EndTermView(session, self.ctx, channel)
            await channel.send(embed=embed, view=view)
            save_game_state()


async def veto_power(ctx, session, channel):
    global user_cache
    president = user_cache[session['president']]
    chancellor = user_cache[session['chancellor']]

    await channel.send(f"{president.mention} and {chancellor.mention}, you may now veto a policy if you both agree.")

    # Present the veto option to the Chancellor
    view = VetoView(ctx, president, chancellor, session, channel)
    await chancellor.send("Do you wish to veto the remaining policies?", view=view)


class VetoView(View):
    def __init__(self, ctx, selected_policy, president, chancellor, session, channel):
        super().__init__()
        self.ctx = ctx
        self.president = president
        self.chancellor = chancellor
        self.session = session
        self.channel = channel
        self.selected_policy = selected_policy

    @discord.ui.button(label="Veto", style=discord.ButtonStyle.red)
    async def veto(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.chancellor.id:
            await interaction.response.send_message("Only the Chancellor can initiate a veto.", ephemeral=True)
            return

        await interaction.response.send_message("You have chosen to veto the policies. Awaiting the President's approval.")
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        # Wait for the President's decision
        view = ConfirmVetoView(self.ctx, self.selected_policy, self.president,
                               self.session, self.channel)
        await self.president.send("The Chancellor has chosen to veto the policies. Do you agree to the veto?", view=view)
    # no veto:

    @discord.ui.button(label="No Veto", style=discord.ButtonStyle.green)
    async def no_veto(self, interaction: discord.Interaction, button: discord.ui.Button):
        global user_cache
        if interaction.user.id != self.chancellor.id:
            await interaction.response.send_message("Only the Chancellor can initiate a veto.", ephemeral=True)
            return

        await interaction.response.send_message("You have chosen not to veto the policies. Proceeding with policy enactment.")
        if session['state'] != 'policy_enactment' or interaction.user.id != session['chancellor']:
            await interaction.user.send("You cannot enact policies at this time.", ephemeral=True)
            return
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        policy = self.selected_policy

        chancellor = user_cache[session["chancellor"]]
        # Enact the policy and reset for the next round
        enacted_policy = policy
        global stats
        stats[interaction.user.id]['policies_enacted'][enacted_policy] += 1
        self.session.get('policies', []).remove(enacted_policy)
        await chancellor.send(
            f"You have enacted the **{enacted_policy}** policy!  Head over to {channel.mention}")
        if enacted_policy == 'Fascist':
            color = discord.Color.red()
        elif enacted_policy == 'Liberal':
            color = discord.Color.blue()
        elif enacted_policy == 'Communist':
            color = 0xff0000
        elif enacted_policy == 'Anarchist':
            color = 0x000000
        elif enacted_policy.startswith("Anti"):
            color = discord.Color.darker_grey()
        embed = discord.Embed(
            title="Policy Enacted",
            description=f"A **{enacted_policy}** Policy has been enacted.",
            color=color
        )
        policy_card = f"GameAssets/{enacted_policy} Article.png"
        if os.path.isfile(policy_card):
            file = discord.File(policy_card, filename="policy.png")
            embed.set_image(url="attachment://policy.png")
            await channel.send(embed=embed, file=file)

        await self.handle_policy_enactment()

    async def handle_policy_enactment(self):
        global user_cache
        enacted_policy = self.selected_policy
        try:
            if enacted_policy == "Anti Communist":
                if 'Communist' in session['enacted_policies']:
                    session['enacted_policies'].remove('Communist')
                session['enacted_policies'].append('Fascist')
            elif enacted_policy == 'Anti Fascist':
                if 'Fascist' in session['enacted_policies']:
                    session['enacted_policies'].remove('Fascist')
                session['enacted_policies'].append('Communist')
            else:
                session['enacted_policies'].append(enacted_policy)
        except KeyError:
            if enacted_policy == "Anti Communist":
                session['enacted_policies'] = ['Fascist']
            elif enacted_policy == 'Anti Fascist':

                session['enacted_policies'] = ['Communist']
            else:
                session['enacted_policies'] = [enacted_policy]
        policies_remaining = session['policies_drawn']
        if enacted_policy:
            policies_remaining.remove(enacted_policy)
            session['discard_pile'].extend(policies_remaining)
            for policy in policies_remaining:
                self.session.get('policies', []).remove(policy)

        # Check for game end conditions
        fasc_count = sum(
            1 for p in session['enacted_policies'] if p == 'Fascist')
        lib_count = sum(
            1 for p in session['enacted_policies'] if p == 'Liberal')
        comm_count = sum(
            1 for p in session['enacted_policies'] if p == 'Communist')
        anar_count = sum(
            1 for p in session['enacted_policies'] if p == 'Anarchist')
        fasc_tracker = f"GameAssets/Fascist Tracker {fasc_count}.png"
        lib_tracker = f"GameAssets/Liberal Tracker {
            session['election_tracker']}-{lib_count}.png"
        comm_tracker = f"GameAssets/Communist Tracker {
            comm_count+anar_count}-{anar_count}.png"
        if os.path.isfile(fasc_tracker):
            file = discord.File(fasc_tracker, filename="fasctracker.png")
            await channel.send(file=file)
        if os.path.isfile(lib_tracker):
            file = discord.File(lib_tracker, filename="libtracker.png")
            await channel.send(file=file)
        if os.path.isfile(comm_tracker) and session.get('mode', 'Normal') == 'XL':
            file = discord.File(comm_tracker, filename="commtracker.png")
            await channel.send(file=file)

        powers = ['investigate_loyalty',
                  'call_special_election', 'policy_peek', 'execution']
        # check number of policies employed that are fascist:
        session['last_government'] = {
            'president': session['president'], 'chancellor': session['chancellor']}

        # Determine the executive action based on the number of players and policies
        if await check_win(self.ctx, self.session, self.channel):
            if enacted_policy in ['Fascist', 'Anti Communist']:
                session['executive_action'] = ""
                if len(session['players']) >= 9:
                    if fasc_count == 1:
                        session['executive_action'] = powers[0]
                    elif fasc_count == 2:
                        session['executive_action'] = powers[0]
                    elif fasc_count == 3:
                        session['executive_action'] = powers[1]
                    elif fasc_count >= 4:
                        session['executive_action'] = powers[3]
                elif len(session['players']) in [7, 8]:
                    if fasc_count == 2:
                        session['executive_action'] = powers[0]
                    elif fasc_count == 3:
                        session['executive_action'] = powers[1]
                    elif fasc_count >= 4:
                        session['executive_action'] = powers[3]
                elif len(session['players']) <= 6:
                    if fasc_count == 3:
                        session['executive_action'] = powers[2]
                    elif fasc_count >= 4:
                        session['executive_action'] = powers[3]
                await handle_executive_action(self.ctx, session, channel)
            elif enacted_policy in ['Communist', 'Anti Fascist']:
                session['communist_action'] = ""
                # #test
                # if len(session['players']) <= 4:
                #     session['communist_action'] = "bugging"
                if comm_count + anar_count == 1:
                    session['communist_action'] = "bugging"
                elif comm_count + anar_count == 2:
                    session['communist_action'] = "radicalization"
                elif comm_count + anar_count == 3:
                    session['communist_action'] = "five_year_plan"
                elif comm_count + anar_count == 4:
                    session['communist_action'] = "congress"
                elif comm_count + anar_count == 5:
                    session['communist_action'] = 'confession'
                await handle_communist_power(self.ctx, session, channel)
            else:
                self.session['state'] = 'new_round'
                self.session['pressed_button'] = False
                president = user_cache[self.session['president']]
                view = PropagandaView(
                    self.ctx, session['policies'], self.session, self.channel)
                if self.session.get('mode', 'Normal') == 'XL' and not self.session.get('propaganda', False):
                    await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

                await asyncio.sleep(10)
                if self.session['state'] == 'new_round' and not self.session.get('pressed_button', False):
                    embed = discord.Embed(
                        title="End of Term",
                        description=f"President {
                            president.mention}, your term is ending. Click the button below to proceed.",
                        color=discord.Color.blue()
                    )
                    # Add the button to end the term
                    view = EndTermView(session, self.ctx, channel)
                    await channel.send(embed=embed, view=view)

                    save_game_state()


class PlayerSelect(discord.ui.Select):
    def __init__(self, players, session, placeholder):
        self.session = session
        self.selected_player_id = None  # Store the selected player's ID

        options = [discord.SelectOption(
            label=user.display_name, value=str(user.id)) for user in players]
        super().__init__(placeholder=placeholder,
                         min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        global user_cache
        # Store the selected player ID but don't proceed yet
        self.selected_player_id = int(self.values[0])
        selected_player = user_cache[self.selected_player_id]
        await interaction.response.send_message(
            f"You have selected {selected_player.mention}. Please click 'Lock In' to confirm.", ephemeral=True)


class InvestigateLoyaltyView(View):
    def __init__(self, ctx, players, session, channel):
        super().__init__()
        self.ctx = ctx
        self.session = session
        self.channel = channel
        self.select = PlayerSelect(
            players, session, placeholder="Select a player to investigate...")
        self.add_item(self.select)
        self.add_item(LockInButton())

    async def lock_in_investigation(self, interaction: discord.Interaction):
        global user_cache
        player_id = self.select.selected_player_id
        if not player_id:
            await interaction.response.send_message("Please select a player first.", ephemeral=True)
            return

        player = user_cache[player_id]
        president = user_cache[self.session['president']]
        await interaction.response.defer()
        await interaction.followup.send(f"Locked in. Investigating {player.mention}.")
        # Show the President the Party Membership of the selected player
        party_membership = self.session['roles'][player_id]
        if party_membership in ["Hitler", "Fascist"]:
            party_membership = "Fascist"
            color = discord.Color.orange()
        elif party_membership == "Liberal":
            color = discord.Color.blue()
        elif party_membership == "Communist":
            color = discord.Color.red()
        elif party_membership == 'Capitalist':
            party_membership = 'Liberal'
            color = discord.Color.blue()
        elif party_membership == "Anarchist":
            color = 0x000000
        elif party_membership == "Monarchist":
            color = discord.Color.purple()
        membership = f"GameAssets/{party_membership} Membership.png"
        membership_embed = discord.Embed(
            title=f"{player.display_name}'s Party Membership",
            description=f"{
                player.display_name} belongs to the **{party_membership}** party!",
            color=color
        )
        if os.path.isfile(membership):
            file = discord.File(membership, filename="membership.png")
            membership_embed.set_thumbnail(url="attachment://membership.png")
            await president.send(embed=membership_embed, file=file)
        # await president.send(f"The party membership of {player.name} is **{party_membership}**.")
        await self.channel.send(f"{president.mention} has completed an investigation of {player.mention}.")

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        self.session['state'] = 'new_round'
        self.session['pressed_button'] = False
        president = user_cache[self.session['president']]
        view = PropagandaView(
            self.ctx, self.session['policies'], self.session, self.channel)
        if self.session.get('mode', 'Normal') == 'XL' and not self.session.get('propaganda', False):
            await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

        await asyncio.sleep(10)
        if self.session['state'] == 'new_round' and not self.session.get('pressed_button', False):
            embed = discord.Embed(
                title="End of Term",
                description=f"President {
                    president.mention}, your term is ending. Click the button below to proceed.",
                color=discord.Color.blue()
            )

            # Add the button to end the term
            view = EndTermView(session, self.ctx, channel)
            await channel.send(embed=embed, view=view)
            save_game_state()


class SpecialElectionView(View):
    def __init__(self, ctx, players, session, channel):
        super().__init__()
        self.ctx = ctx
        self.session = session
        self.channel = channel
        self.select = PlayerSelect(
            players, session, placeholder="Select a player to become the next Presidential Candidate...")
        self.add_item(self.select)
        self.add_item(LockInButton())

    async def lock_in_special_election(self, interaction: discord.Interaction):
        global user_cache
        selected_player_id = self.select.selected_player_id
        if not selected_player_id:
            await interaction.response.send_message("Please select a player first.", ephemeral=True)
            return

        selected_player = user_cache[selected_player_id]
        self.session['special_election'] = True
        self.session['prev_president'] = interaction.user.id
        self.session['president'] = selected_player_id
        await interaction.response.defer()
        await interaction.followup.send(f"Locked in. Electing {selected_player.mention}.")
        await self.channel.send(f"{selected_player.mention} has been selected as the next Presidential Candidate.")

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        session['chancellor'] = None
        session['chancellor_candidate'] = None
        await start_election_round(self.ctx, session, channel)


class EndTermView(View):
    def __init__(self, session, ctx, channel):
        super().__init__(timeout=None)
        self.session = session
        self.ctx = ctx
        self.channel = channel

    @discord.ui.button(label="End Term", style=discord.ButtonStyle.red)
    async def end_term(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.session['president']:
            await interaction.response.send_message("Only the current President can end their term.", ephemeral=True)
            return
        if self.session['state'] == 'execution':
            await interaction.response.send_message("You cannot end your term during an execution.", ephemeral=True)
            return
        embed = discord.Embed(
            title="Presidential Term Ended",
            description="The current Presidential term has ended.",
            color=discord.Color.green()
        )
        self.session['pressed_button'] = True
        await interaction.response.send_message(embed=embed)

        # Disable the button after the term is ended
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        # Proceed to the next round
        await self.start_next()

    async def start_next(self):
        # Logic to start the next round
        self.session['state'] = 'new_round'
        await start_next_round(self.ctx, self.session, self.channel)


class ExecutionView(View):
    def __init__(self, ctx, players, session, channel):
        super().__init__()
        self.ctx = ctx
        self.session = session
        self.channel = channel
        self.select = PlayerSelect(
            players, session, placeholder="Select a player to execute...")
        self.add_item(self.select)
        self.add_item(LockInButton())

    async def lock_in_execution(self, interaction: discord.Interaction):
        global user_cache
        executed_player_id = self.select.selected_player_id
        if not executed_player_id:
            await interaction.response.send_message("Please select a player first.", ephemeral=True)
            return

        save_game_state()
        executed_player = user_cache[executed_player_id]
        await interaction.response.defer()
        await interaction.followup.send(f"Locked in. Executing <@{executed_player_id}>.")
        description = f"## The doors of the parliament swing open as President <@{
            interaction.user.id}> strides in with authority."

        exec_embed = discord.Embed(
            title="The President speaks..",
            description=description,
            color=discord.Color.yellow()
        )
        msg = await self.channel.send(embed=exec_embed)
        await asyncio.sleep(2)
        description += f"\n\n*The room falls into a tense silence as all eyes turn to the leader.*"
        exec_embed.description = description
        exec_embed.color = discord.Color.orange()
        await msg.edit(embed=exec_embed)
        await asyncio.sleep(2)
        description += f"\n\nWith a voice that echoes through the chambers, the President declares:"
        exec_embed.description = description
        exec_embed.color = discord.Color.red()
        await msg.edit(embed=exec_embed)
        await asyncio.sleep(2)
        description += f"\n\n### \"In the name of the Republic, and for the future of our people, I hereby formally execute <@{
            executed_player_id}>\"."
        exec_embed.description = description
        exec_embed.color = 0xff0000
        exec_embed.set_thumbnail(url=executed_player.avatar)
        president_killed = False
        if executed_player_id == self.session['president']:
            players = self.session['players']
            current_president_index = players.index(self.session['president'])
            next_president_index = (current_president_index + 1) % len(players)
            self.session['president'] = players[next_president_index]
            president_killed = True

        self.session['executed_players'] = self.session.get(
            'executed_players', [])
        self.session['executed_players'].append(executed_player_id)
        self.session['players'].remove(executed_player_id)
        await msg.edit(embed=exec_embed)
        # Check if the executed player is Hitler
        if not await check_win(self.ctx, self.session, self.channel, executed_player_id, self.session['president']):
            return
        await self.channel.send("The executed player was not Hitler. The game continues.")
        if self.session['roles'][executed_player_id] == 'Capitalist':
            self.session['policies'].extend(['Communist'])
            random.shuffle(self.session['policies'])

        # Adjust permissions for the executed player
        await self.channel.set_permissions(executed_player, send_messages=False, add_reactions=False, read_messages=True)
        if executed_player_id in self.session.get('last_government', {}).values():
            # set that value as none:
            if executed_player_id == session["last_government"]["president"]:
                session["last_government"]["president"] = None
            else:
                session["last_government"]["chancellor"] = None

        save_game_state()

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        self.session['state'] = 'new_round'
        self.session['pressed_button'] = False
        president = user_cache[self.session['president']]
        view = PropagandaView(
            self.ctx, self.session['policies'], self.session, self.channel)
        if not self.session.get('propaganda', False) and not president_killed:
            await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

        await asyncio.sleep(10)
        if president_killed:
            embed = discord.Embed(
                title="End of Term",
                description=f"Since the president was shot dead.. We move to the next president by hierarchy.",
                color=discord.Color.red()
            )
            await self.channel.send(embed=embed)
            await asyncio.sleep(5)
            await start_election_round(self.ctx, session, channel)
        elif session['state'] == 'new_round' and not session.get('pressed_button', False):
            embed = discord.Embed(
                title="End of Term",
                description=f"President {
                    president.mention}, your term is ending. Click the button below to proceed.",
                color=discord.Color.blue()
            )

            # Add the button to end the term
            view = EndTermView(session, self.ctx, channel)
            await channel.send(embed=embed, view=view)
            save_game_state()


class BuggingView(View):
    def __init__(self, ctx, players, non_communist_players, session, channel):
        super().__init__()
        self.ctx = ctx
        self.session = session
        self.channel = channel
        self.players = players
        self.timer_task = None

        self.select = PlayerSelect(
            non_communist_players, session, placeholder="Select a player to bug...")
        self.add_item(self.select)
        self.add_item(LockInButton())

        # Automatically proceed if there's only one Communist
        if sum(1 for p in session['players'] if session['roles'][p] == 'Communist') == 1:
            asyncio.create_task(self.finish_bugging())

    async def lock_in_bugging(self, interaction: discord.Interaction):
        bugged_player_id = self.select.selected_player_id
        session = self.session

        if 'bug_votes' not in session:
            session['bug_votes'] = {}

        if not bugged_player_id:
            await interaction.response.send_message("Please select a player first.", ephemeral=True)
            return

        if session['roles'][interaction.user.id] != 'Communist':
            await interaction.response.send_message("Only Communists can bug a player. You are not Communist!", ephemeral=True)
            return

        session['bug_votes'][interaction.user.id] = bugged_player_id
        await interaction.response.send_message(f"You have voted to bug <@{bugged_player_id}>.", ephemeral=True)

        # Disable the button and dropdown for the user after voting
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        # Start timer if not already started
        if not self.timer_task:
            self.timer_task = asyncio.create_task(
                self.finish_bugging_after_timeout())

        # Check if all Communists have voted
        if len(session['bug_votes']) == sum(1 for p in self.players if session['roles'][p.id] == 'Communist'):
            await self.finish_bugging()

    async def finish_bugging_after_timeout(self):
        await asyncio.sleep(30)
        await self.finish_bugging()

    async def finish_bugging(self):
        if self.timer_task:
            self.timer_task.cancel()

        if len(self.session['bug_votes']) == 0:
            await self.channel.send("No votes were cast for bugging. The bugging action is skipped.")
            return

        # Count votes
        vote_count = {}
        for player_id in self.session['bug_votes'].values():
            vote_count[player_id] = vote_count.get(player_id, 0) + 1

        # Determine the player to be bugged
        max_votes = max(vote_count.values())
        candidates = [player_id for player_id,
                      votes in vote_count.items() if votes == max_votes]
        bugged_player_id = random.choice(candidates) if len(
            candidates) > 1 else candidates[0]

        await self.reveal_party_membership(bugged_player_id)

    async def reveal_party_membership(self, bugged_player_id):
        bugged_player = user_cache[bugged_player_id]
        role = self.session['roles'][bugged_player_id]

        party_membership = role
        if party_membership in ["Hitler", "Fascist", "Capitalist"]:
            party_membership = "Fascist"
            color = discord.Color.orange()
        elif party_membership == "Liberal":
            color = discord.Color.blue()
        elif party_membership == "Communist":
            color = discord.Color.red()
        elif party_membership == "Anarchist":
            color = 0x000000
        elif party_membership == "Monarchist":
            color = discord.Color.purple()

        membership_image = f"GameAssets/{party_membership} Membership.png"
        embed = discord.Embed(
            title="Bugging Result",
            description=f"The party membership of {
                bugged_player.mention} is {party_membership}!",
            color=color
        )

        if os.path.isfile(membership_image):
            with open(membership_image, 'rb') as file:
                discord_file = discord.File(file, filename="membership.png")
                embed.set_thumbnail(url="attachment://membership.png")
                for player in self.players:
                    if self.session['roles'][player.id] == 'Communist':
                        await player.send(embed=embed, file=discord_file)
        else:
            for player in self.players:
                if self.session['roles'][player.id] == 'Communist':
                    await player.send(embed=embed)

        # Reset session state
        self.session['bug_votes'] = {}

        if self.session['communism']:
            president = user_cache[self.session['president']]
            embed = discord.Embed(
                title="End of Term",
                description=f"President {
                    president.mention}, your term is ending. Click the button below to proceed.",
                color=discord.Color.blue()
            )
            view = EndTermView(self.session, self.ctx, self.channel)
            await self.channel.send(embed=embed, view=view)

            save_game_state()

        self.session['communism'] = False



class RadicalizationView(View):
    def __init__(self, ctx, players, non_communist_players, session, channel):
        super().__init__()
        self.ctx = ctx
        self.session = session
        self.channel = channel
        self.players = players
        self.non_communist_players = non_communist_players
        self.timer_task = None

        self.select = PlayerSelect(
            non_communist_players, session, placeholder="Select a player to radicalize...")
        self.add_item(self.select)
        self.add_item(LockInButton())

        # Automatically proceed if there's only one Communist
        if sum(1 for p in session['players'] if session['roles'][p] == 'Communist') == 1:
            asyncio.create_task(self.finish_radicalizing())

    async def lock_in_radicalization(self, interaction: discord.Interaction):
        global user_cache
        radicalized_player_id = self.select.selected_player_id
        session = self.session

        if 'radicalize_votes' not in session:
            session['radicalize_votes'] = {}

        if not radicalized_player_id:
            await interaction.response.send_message("Please select a player first.", ephemeral=True)
            return

        if session['roles'][interaction.user.id] != 'Communist':
            await interaction.response.send_message("Only Communists can radicalize a player. You are not Communist!", ephemeral=True)
            return

        session['radicalize_votes'][interaction.user.id] = radicalized_player_id
        await interaction.response.send_message(f"You have voted to radicalize <@{radicalized_player_id}>.", ephemeral=True)

        # Disable the button and dropdown for the user after voting
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        # Start timer if not already started
        if not self.timer_task:
            self.timer_task = asyncio.create_task(
                self.finish_radicalizing_after_timeout())

        # Check if all Communists have voted
        if len(session['radicalize_votes']) == sum(1 for p in self.players if session['roles'][p.id] == 'Communist'):
            await self.finish_radicalizing()

    async def finish_radicalizing_after_timeout(self):
        await asyncio.sleep(30)
        await self.finish_radicalizing()

    async def finish_radicalizing(self):
        if self.timer_task:
            self.timer_task.cancel()

        if len(self.session['radicalize_votes']) == 0:
            await self.channel.send("No votes were cast for radicalizing. The radicalization action is skipped.")
            return

        # Count votes
        vote_count = {}
        for player_id in self.session['radicalize_votes'].values():
            vote_count[player_id] = vote_count.get(player_id, 0) + 1

        # Determine the player to be radicalized
        max_votes = max(vote_count.values())
        candidates = [player_id for player_id,
                      votes in vote_count.items() if votes == max_votes]
        radicalized_player_id = random.choice(
            candidates) if len(candidates) > 1 else candidates[0]

        await self.radicalize_member(radicalized_player_id)

    async def radicalize_member(self, radicalized_player_id):
        global user_cache
        radicalized_player = user_cache[radicalized_player_id]
        role = self.session['roles'][radicalized_player_id]

        embed = discord.Embed(
            title="Radicalizing Result",
            description=f"An attempt to turn {
                radicalized_player.mention} into a Communist has been launched!",
            color=discord.Color.red()
        )

        membership_image = "GameAssets/Communist Membership.png"
        if os.path.isfile(membership_image):
            for player in self.players:
                with open(membership_image, 'rb') as file:
                    discord_file = discord.File(
                        file, filename="membership.png")
                    embed.set_thumbnail(url="attachment://membership.png")
                    if self.session['roles'][player.id] == 'Communist':
                        await player.send(embed=embed, file=discord_file)
        else:
            for player in self.players:
                if self.session['roles'][player.id] == 'Communist':
                    await player.send(embed=embed)

        # Reset session state
        self.session['radicalize_votes'] = {}

        if role in ["Hitler", "Capitalist", "Fascist"]:
            fail_embed = discord.Embed(
                title="Radicalization Failed",
                description=f"There was an attempt to radicalize you, but it failed. You can never be Communist.",
                color=discord.Color.green()
            )
            await radicalized_player.send(embed=fail_embed)
        else:
            success_embed = discord.Embed(
                title="Radicalization Successful",
                description=f"You have been successfully radicalized. Welcome to the Communist party.",
                color=0xff0000
            )
            if os.path.isfile(membership_image):
                with open(membership_image, 'rb') as file:
                    discord_file = discord.File(
                        file, filename="membership.png")
                    success_embed.set_thumbnail(
                        url="attachment://membership.png")
                    await radicalized_player.send(embed=success_embed, file=discord_file)
            self.session['roles'][radicalized_player_id] = 'Communist'

        # Notify the end of the term
        president = user_cache[self.session['president']]
        embed = discord.Embed(
            title="End of Term",
            description=f"President {
                president.mention}, your term is ending. Click the button below to proceed.",
            color=discord.Color.blue()
        )
        view = EndTermView(self.session, self.ctx, self.channel)
        await self.channel.send(embed=embed, view=view)

        save_game_state()

        # Reset communism flag
        self.session['communism'] = False


async def handle_communist_power(ctx, session, channel):
    global user_cache
    president = user_cache[session['president']]
    players = []
    guild = bot.get_guild(session['guild_id'])
    for member in guild.members:  # Use the fetched guild object
        # and session['roles'][member.id] != 'Communist':
        if member.id in session['players']:
            players.append(member)
    non_communist_players = []
    for member in guild.members:
        if member.id in session['players'] and session['roles'][member.id] != 'Communist':
            non_communist_players.append(member)
    if session.get('communist_action') == 'confession':
        desc = f"The party membership of the president, {
            president.mention} is..."
        embed = discord.Embed(
            title="Confession",
            description=desc,
            color=0xffffff
        )
        emb = await channel.send(embed=embed)
        await asyncio.sleep(4)
        party_membership = session['roles'][session['president']]
        if party_membership in ["Hitler", "Fascist"]:
            party_membership = "Fascist"
            color = discord.Color.orange()
        elif party_membership == "Liberal":
            color = discord.Color.blue()
        elif party_membership == "Communist":
            color = discord.Color.red()
        elif party_membership == 'Capitalist':
            color = discord.Color.gold()
        elif party_membership == "Anarchist":
            color = 0x000000
        elif party_membership == "Monarchist":
            color = discord.Color.purple()
        membership = f"GameAssets/{party_membership} Membership.png"
        desc += f"\n\n# {party_membership}!!"
        embed.description = desc
        embed.color = color
        if os.path.isfile(membership):
            file = discord.File(membership, filename="membership.png")
            embed.set_thumbnail(url="attachment://membership.png")
            await emb.edit(embed=embed, file=file)
        # end term:
        session['state'] = 'new_round'
        session['pressed_button'] = False
        view = PropagandaView(ctx, session['policies'], session, channel)
        if session.get('mode', 'Normal') == 'XL' and not session.get('propaganda', False):
            await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

        await asyncio.sleep(10)

        if session['state'] == 'new_round' and not session.get('pressed_button', False):
            embed = discord.Embed(
                title="End of Term",
                description=f"President {
                    president.mention}, your term is ending. Click the button below to proceed.",
                color=discord.Color.blue()
            )
            # Add the button to end the term
            view = EndTermView(session, ctx, channel)
            await channel.send(embed=embed, view=view)
            save_game_state()

    elif session.get('communist_action') == 'bugging':
        # Send DM to all Communists for discussion
        await channel.send(f"Communist power to bug a player has now been unlocked. Communists, Please proceed in DMs. ")
        for player in players:
            if session['roles'][player.id] == 'Communist':
                view = BuggingView(
                    ctx, players, non_communist_players, session, channel)
                await player.send("Communists, please select a player to bug using the interface below:", view=view)
                await player.send("You may use this DM to communicate with other Communists to decide on who to bug.")
        # Start the Bugging voting process
        session['communism'] = True
        await channel.send(embed=embed, view=view)
        save_game_state()
        # Save game state
        save_game_state()
    elif session.get('communist_action') == 'radicalization':
        await channel.send(f"Communist power to radicalize a player has now been unlocked. Communists, Please proceed in DMs. ")
        for player in players:
            if session['roles'][player.id] == 'Communist':
                view = RadicalizationView(
                    ctx, players, non_communist_players, session, channel)
                await player.send("Communists, please select a player to radicalize using the interface below:", view=view)
                await player.send("You may use this DM to communicate with other Communists to decide on who to radicalize.")
        # Start the Bugging voting process
        session['communism'] = True
        save_game_state()
    elif session.get('communist_action') == 'five_year_plan':
        await channel.send(f"A five year plan has been enacted! 2 communst policies and 1 liberal policy has been added to the deck.")
        session['policies'].extend(['Communist', 'Communist', 'Liberal'])
        random.shuffle(session['policies'])

        session['state'] = 'new_round'
        session['pressed_button'] = False
        view = PropagandaView(ctx, session['policies'], session, channel)
        if session.get('mode', 'Normal') == 'XL' and not session.get('propaganda', False):
            await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

        await asyncio.sleep(10)
        if session['state'] == 'new_round' and not session.get('pressed_button', False):
            embed = discord.Embed(
                title="End of Term",
                description=f"President {
                    president.mention}, your term is ending. Click the button below to proceed.",
                color=discord.Color.blue()
            )
            # Add the button to end the term
            view = EndTermView(session, ctx, channel)
            await channel.send(embed=embed, view=view)
            save_game_state()
    elif session.get('communist_action') == 'congress':
        await channel.send("The Communist Congress session takes places. The new Communist identifies the existing communists.")
        commies = []
        for player in players:
            if session['roles'][player.id] == 'Communist':
                commies.append(f"**<@{player.id}>**")
        for player in players:
            if session['roles'][player.id] == 'Communist':
                await player.send(f"The Communist party has the following members: {', '.join(commies)}")
        session['state'] = 'new_round'
        session['pressed_button'] = False
        president = user_cache[session['president']]
        view = PropagandaView(ctx, session['policies'], session, channel)
        if session.get('mode', 'Normal') == 'XL' and not session.get('propaganda', False):
            await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

        await asyncio.sleep(10)
        if session['state'] == 'new_round' and not session.get('pressed_button', False):
            embed = discord.Embed(
                title="End of Term",
                description=f"President {
                    president.mention}, your term is ending. Click the button below to proceed.",
                color=discord.Color.blue()
            )
            # Add the button to end the term
            view = EndTermView(session, ctx, channel)
            await channel.send(embed=embed, view=view)
            save_game_state()


async def handle_executive_action(ctx, session, channel):
    global user_cache
    president = user_cache[session['president']]
    players = []
    guild = bot.get_guild(session['guild_id'])
    for member in guild.members:  # Use the fetched guild object
        if member.id in session['players']:
            players.append(member)

    if session.get('executive_action') == 'investigate_loyalty':
        await channel.send(f"{president.mention}, you have the power to investigate the loyalty of one player.")
        view = InvestigateLoyaltyView(ctx, players, session, channel)
        await president.send("Select a player to investigate their loyalty:", view=view)

    elif session.get('executive_action') == 'call_special_election':
        await channel.send(f"{president.mention}, you have the power to call a special election.")
        view = SpecialElectionView(ctx, players, session, channel)
        await president.send("Select a player to become the next Presidential Candidate:", view=view)

    elif session.get('executive_action') == 'policy_peek':
        await channel.send(f"{president.mention}, you have the power to peek at the top three policies.")
        top_policies = session.get('policies', [])[:3]
        await president.send(f"The top three policies in the deck are: {', '.join(top_policies)}.")
        await channel.send(f"{president.mention} has peeked at the top three policies.")
        session['state'] = 'new_round'
        session['pressed_button'] = False
        president = user_cache[session['president']]
        view = PropagandaView(ctx, session['policies'], session, channel)
        if session.get('mode', 'Normal') == 'XL' and not session.get('propaganda', False):
            await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

        await asyncio.sleep(10)
        if session['state'] == 'new_round' and not session.get('pressed_button', False):
            president = user_cache[session['president']]
            embed = discord.Embed(
                title="End of Term",
                description=f"President {
                    president.mention}, your term is ending. Click the button below to proceed.",
                color=discord.Color.blue()
            )
            # Add the button to end the term
            view = EndTermView(session, ctx, channel)
            await channel.send(embed=embed, view=view)
            save_game_state()
    elif session.get('executive_action') == 'execution':
        await channel.send(f"{president.mention}, you have the power to execute one player.")
        view = ExecutionView(ctx, players, session, channel)
        await president.send("Select a player to execute:", view=view)

    else:
        await channel.send(f"No executive action to perform. Proceeding to the next round.")
        session['state'] = 'new_round'
        session['pressed_button'] = False
        president = user_cache[session['president']]
        view = PropagandaView(ctx, session['policies'], session, channel)
        if session.get('mode', 'Normal') == 'XL' and not session.get('propaganda', False):
            await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

        await asyncio.sleep(10)
        if session['state'] == 'new_round' and not session.get('pressed_button', False):
            embed = discord.Embed(
                title="End of Term",
                description=f"President {
                    president.mention}, your term is ending. Click the button below to proceed.",
                color=discord.Color.blue()
            )

            # Add the button to end the term
            view = EndTermView(session, ctx, channel)
            await channel.send(embed=embed, view=view)


async def handle_failed_election(ctx, session, channel):
    global user_cache
    session['election_tracker'] += 1
    await channel.send(f"The election has failed. The Election Tracker is now at {session['election_tracker']}.")

    if session['election_tracker'] >= 3:
        await enact_top_policy_due_to_chaos(ctx, session, channel)
    else:
        session['state'] = 'new_round'
        session['pressed_button'] = False
        president = user_cache[session['president']]
        view = PropagandaView(ctx, session['policies'], session, channel)
        if session.get('mode', 'Normal') == 'XL' and not session.get('propaganda', False):
            await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

        await asyncio.sleep(10)
        if session['state'] == 'new_round' and not session.get('pressed_button', False):
            embed = discord.Embed(
                title="End of Term",
                description=f"President {
                    president.mention}, your term is ending. Click the button below to proceed.",
                color=discord.Color.blue()
            )
            # Add the button to end the term
            view = EndTermView(session, ctx, channel)
            await channel.send(embed=embed, view=view)

            save_game_state()


async def enact_top_policy_due_to_chaos(ctx, session, channel):
    global user_cache
    if len(session.get('policies', [])) == 0:
        # If the policy deck is empty, shuffle the discard pile back into the policy deck
        session.get('policies', []).extend(session.get('discard_pile', []))
        session['discard_pile'] = []
        random.shuffle(session.get('policies', []))

    # Enact the top policy automatically
    top_policy = session.get('policies', []).pop(0)
    session['enacted_policies'].append(top_policy)
    session['election_tracker'] = 0  # Reset the Election Tracker

    # Announce the policy that has been enacted
    await channel.send(f"Three elections have failed. The country is in chaos, and the top policy has been enacted.")
    if top_policy == 'Fascist':
        color = discord.Color.red()
    else:
        color = discord.Color.blue()
    embed = discord.Embed(
        title="Policy Enacted",
        description=f"The top policy was... **{top_policy}**!! .",
        color=color
    )
    policy_card = f"GameAssets/{top_policy} Article.png"
    if os.path.isfile(policy_card):
        file = discord.File(policy_card, filename="policy.png")
        embed.set_image(url="attachment://policy.png")
        await channel.send(embed=embed, file=file)
    session['state'] = 'new_round'
    session['pressed_button'] = False
    president = user_cache[session['president']]
    view = PropagandaView(ctx, session['policies'], session, channel)
    if session.get('mode', 'Normal') == 'XL' and not session.get('propaganda', False):
        await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

    await asyncio.sleep(10)
    if session['state'] == 'new_round' and not session.get('pressed_button', False):
        embed = discord.Embed(
            title="End of Term",
            description=f"President {
                president.mention}, your term is ending. Click the button below to proceed.",
            color=discord.Color.blue()
        )
        # Add the button to end the term
        view = EndTermView(session, ctx, channel)
        await channel.send(embed=embed, view=view)
        save_game_state()


class ConfirmVetoView(View):
    def __init__(self, ctx, selected_policy, president, session, channel):
        super().__init__()
        self.ctx = ctx
        self.president = president
        self.session = session
        self.channel = channel
        self.selected_policy = selected_policy

    @discord.ui.button(label="Agree to Veto", style=discord.ButtonStyle.green)
    async def agree(self, interaction: discord.Interaction, button: discord.ui.Button):
        global user_cache
        if interaction.user.id != self.president.id:
            await interaction.response.send_message("Only the President can agree to the veto.", ephemeral=True)
            return

        await interaction.response.send_message("You have agreed to the veto. The policies are discarded, and the Election Tracker advances.")

        # Discard the policies drawn and advance the Election Tracker
        self.session['discard_pile'].extend(
            self.session.get('policies_drawn', []))
        for p in self.session['policies_drawn']:
            self.session.get('policies', []).remove(p)
        self.session['policies_drawn'] = []
        self.session['election_tracker'] += 1

        await self.channel.send(f"The veto has been agreed upon. The Election Tracker is now at {self.session['election_tracker']}.")
        # disable button:
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        if self.session['election_tracker'] >= 3:
            await enact_top_policy_due_to_chaos(interaction, self.session, self.channel)
        else:
            session['state'] = 'new_round'
            session['pressed_button'] = False
            president = user_cache[session['president']]
            view = PropagandaView(
                self.ctx, session['policies'], session, channel)
            if session.get('mode', 'Normal') == 'XL' and not session.get('propaganda', False):
                await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

            await asyncio.sleep(10)
            if session['state'] == 'new_round' and not session.get('pressed_button', False):
                embed = discord.Embed(
                    title="End of Term",
                    description=f"President {
                        president.mention}, your term is ending. Click the button below to proceed.",
                    color=discord.Color.blue()
                )
                # Add the button to end the term
                view = EndTermView(session, self.ctx, channel)
                await channel.send(embed=embed, view=view)

                save_game_state()

    @discord.ui.button(label="Reject Veto", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        global user_cache
        if interaction.user.id != self.president.id:
            await interaction.response.send_message("Only the President can reject the veto.", ephemeral=True)
            return

        await interaction.response.send_message("You have rejected the veto. The policy chosen by the Chancellor has been enacted.")

        policy = self.selected_policy

        chancellor = user_cache[session["chancellor"]]
        # Enact the policy and reset for the next round
        enacted_policy = policy
        global stats
        stats[session["chancellor"]]['policies_enacted'][enacted_policy] += 1
        self.session.get('policies', []).remove(enacted_policy)
        await chancellor.send(
            f"You have enacted the **{enacted_policy}** policy!  Head over to {channel.mention}")
        if enacted_policy == 'Fascist':
            color = discord.Color.red()
        elif enacted_policy == 'Liberal':
            color = discord.Color.blue()
        elif enacted_policy == 'Communist':
            color = 0xff0000
        elif enacted_policy == 'Anarchist':
            color = 0x000000
        elif enacted_policy.startswith("Anti"):
            color = discord.Color.darker_grey()
        embed = discord.Embed(
            title="Policy Enacted",
            description=f"A **{enacted_policy}** Policy has been enacted.",
            color=color
        )
        policy_card = f"GameAssets/{enacted_policy} Article.png"
        if os.path.isfile(policy_card):
            file = discord.File(policy_card, filename="policy.png")
            embed.set_image(url="attachment://policy.png")
            await channel.send(embed=embed, file=file)

        # Disable the dropdown after selection
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await self.handle_policy_enactment()

    async def handle_policy_enactment(self):
        global user_cache
        enacted_policy = self.selected_policy
        try:
            if enacted_policy == "Anti Communist":
                if 'Communist' in session['enacted_policies']:
                    session['enacted_policies'].remove('Communist')
                session['enacted_policies'].append('Fascist')
            elif enacted_policy == 'Anti Fascist':
                if 'Fascist' in session['enacted_policies']:
                    session['enacted_policies'].remove('Fascist')
                session['enacted_policies'].append('Communist')
            else:
                session['enacted_policies'].append(enacted_policy)
        except KeyError:
            if enacted_policy == "Anti Communist":
                session['enacted_policies'] = ['Fascist']
            elif enacted_policy == 'Anti Fascist':

                session['enacted_policies'] = ['Communist']
            else:
                session['enacted_policies'] = [enacted_policy]
        policies_remaining = session['policies_drawn']
        if enacted_policy:
            policies_remaining.remove(enacted_policy)
            session['discard_pile'].extend(policies_remaining)
            for policy in policies_remaining:
                self.session.get('policies', []).remove(policy)

        # Check for game end conditions
        fasc_count = sum(
            1 for p in session['enacted_policies'] if p == 'Fascist')
        lib_count = sum(
            1 for p in session['enacted_policies'] if p == 'Liberal')
        comm_count = sum(
            1 for p in session['enacted_policies'] if p == 'Communist')
        anar_count = sum(
            1 for p in session['enacted_policies'] if p == 'Anarchist')
        fasc_tracker = f"GameAssets/Fascist Tracker {fasc_count}.png"
        lib_tracker = f"GameAssets/Liberal Tracker {
            session['election_tracker']}-{lib_count}.png"
        comm_tracker = f"GameAssets/Communist Tracker {
            comm_count+anar_count}-{anar_count}.png"
        if os.path.isfile(fasc_tracker):
            file = discord.File(fasc_tracker, filename="fasctracker.png")
            await channel.send(file=file)
        if os.path.isfile(lib_tracker):
            file = discord.File(lib_tracker, filename="libtracker.png")
            await channel.send(file=file)
        if os.path.isfile(comm_tracker) and session.get('mode', 'Normal') == 'XL':
            file = discord.File(comm_tracker, filename="commtracker.png")
            await channel.send(file=file)

        powers = ['investigate_loyalty',
                  'call_special_election', 'policy_peek', 'execution']
        # check number of policies employed that are fascist:
        session['last_government'] = {
            'president': session['president'], 'chancellor': session['chancellor']}

        # Determine the executive action based on the number of players and policies
        if await check_win(self.ctx, self.session, self.channel):
            if enacted_policy in ['Fascist', 'Anti Communist']:
                session['executive_action'] = ""
                if len(session['players']) >= 9:
                    if fasc_count == 1:
                        session['executive_action'] = powers[0]
                    elif fasc_count == 2:
                        session['executive_action'] = powers[0]
                    elif fasc_count == 3:
                        session['executive_action'] = powers[1]
                    elif fasc_count >= 4:
                        session['executive_action'] = powers[3]
                elif len(session['players']) in [7, 8]:
                    if fasc_count == 2:
                        session['executive_action'] = powers[0]
                    elif fasc_count == 3:
                        session['executive_action'] = powers[1]
                    elif fasc_count >= 4:
                        session['executive_action'] = powers[3]
                elif len(session['players']) <= 6:
                    if fasc_count == 3:
                        session['executive_action'] = powers[2]
                    elif fasc_count >= 4:
                        session['executive_action'] = powers[3]
                await handle_executive_action(self.ctx, session, channel)
            elif enacted_policy in ['Communist', 'Anti Fascist']:
                session['communist_action'] = ""
                # #test
                # if len(session['players']) <= 4:
                #     session['communist_action'] = "bugging"
                if comm_count + anar_count == 1:
                    session['communist_action'] = "bugging"
                elif comm_count + anar_count == 2:
                    session['communist_action'] = "radicalization"
                elif comm_count + anar_count == 3:
                    session['communist_action'] = "five_year_plan"
                elif comm_count + anar_count == 4:
                    session['communist_action'] = "congress"
                elif comm_count + anar_count == 5:
                    session['communist_action'] = 'confession'
                await handle_communist_power(self.ctx, session, channel)
            else:
                self.session['state'] = 'new_round'
                self.session['pressed_button'] = False
                president = user_cache[session['president']]
                view = PropagandaView(
                    self.ctx, self.session['policies'], self.session, self.channel)
                if self.session.get('mode', 'Normal') == 'XL' and not self.session.get('propaganda', False):
                    await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

                await asyncio.sleep(10)
                if self.session['state'] == 'new_round' and not self.session.get('pressed_button', False):

                    embed = discord.Embed(
                        title="End of Term",
                        description=f"President {
                            president.mention}, your term is ending. Click the button below to proceed.",
                        color=discord.Color.blue()
                    )
                    # Add the button to end the term
                    view = EndTermView(session, self.ctx, channel)
                    await channel.send(embed=embed, view=view)

                    save_game_state()


class DiscardPolicy(Select):
    def __init__(self, policies):
        self.selected_policy = None  # Store the selected policy
        options = [discord.SelectOption(
            label=policy, value=f"{policy}-{i}") for i, policy in enumerate(policies)]
        super().__init__(placeholder="Select a policy to discard...",
                         min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Store the selected policy but don't discard it yet
        self.selected_policy = self.values[0].rsplit('-', 1)[0]
        await interaction.response.send_message(
            f"You have selected {self.selected_policy}. Please click 'Lock In' to confirm.", ephemeral=True)


class DiscardPolicyView(View):
    def __init__(self, policies):
        super().__init__()
        self.select = DiscardPolicy(policies)
        self.add_item(self.select)
        self.add_item(LockInButton())

    async def lock_in_policy_discard(self, interaction: discord.Interaction):
        guild_id = channel.guild.id
        session = game_sessions.get(guild_id)

        if session['state'] != 'policy_discard' or interaction.user.id != session['president']:
            await interaction.response.send_message("You cannot discard policies at this time.", ephemeral=True)
            return

        # Extract the policy name from the selected value
        policy = self.select.selected_policy
        if not policy:
            await interaction.response.send_message("Please select a policy first.", ephemeral=True)
            return
        if policy not in session['policies_drawn']:
            await interaction.response.send_message("Invalid policy selected.", ephemeral=True)
            return

        # Remove the selected policy
        # self.session.get('policies',[]).append(policy)
        try:
            session['discard_pile'].extend([policy])
        except KeyError:
            session['discard_pile'] = [policy]
        session['policies_drawn'].remove(policy)
        session.get('policies', []).remove(policy)
        await interaction.response.defer()
        await interaction.followup.send(f"You have discarded the **{policy}** policy. The remaining policies will be sent to the Chancellor.")
        save_game_state()

        # Disable the dropdown after selection
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        # Move to the Chancellor's policy enactment phase
        await enact_policy(interaction, session, session['channel_id'])


async def legislative_session(ctx, session, channel):
    global user_cache
    president = user_cache[session['president']]
    chancellor = user_cache[session['chancellor']]

    # President draws top 3 policies:
    if len(session.get('policies', [])) < 3:
        session.get('policies', []).extend(session.get('discard_pile', []))
        session['discard_pile'] = []
        random.shuffle(session.get('policies', []))
        print("Shuffling...")
    policies_drawn = session.get('policies', [])[:3]
    session['policies_drawn'] = policies_drawn
    policies_drawn_str = ', '.join(str(policy) for policy in policies_drawn)
    await president.send(f"You have drawn these policies: {policies_drawn_str}. Please select one to discard.")
    # Create and send the dropdown
    view = DiscardPolicyView(policies_drawn)

    await president.send(f"{president.mention}, please select a policy to discard from the dropdown below:", view=view)

    session['state'] = 'policy_discard'
    save_game_state()


class EnactPolicySelect(Select):
    def __init__(self, ctx, policies):
        self.ctx = ctx
        self.selected_policy = None  # Store the selected policy
        options = [discord.SelectOption(
            label=policy, value=f"{policy}-{i}") for i, policy in enumerate(policies)]
        super().__init__(placeholder="Select a policy to enact...",
                         min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Store the selected policy but don't enact it yet
        self.selected_policy = self.values[0].rsplit('-', 1)[0]
        await interaction.response.send_message(
            f"You have selected {self.selected_policy}. Please click 'Lock In' to confirm.", ephemeral=True)


class EnactPolicyView(View):
    def __init__(self, ctx, policies):
        super().__init__()
        self.ctx = ctx
        self.select = EnactPolicySelect(ctx, policies)
        self.add_item(self.select)
        self.add_item(LockInButton())

    async def lock_in_policy_enactment(self, interaction: discord.Interaction):
        global enacted_policy, user_cache, stats
        guild_id = channel.guild.id
        session = game_sessions.get(guild_id)
        if session.get('vonc', False) and not session.get('vonc_enacted', False):
            await interaction.response.send_message("Select an option in the vote of no confidence first.", ephemeral=True)
            return
        if len([p for p in session['enacted_policies'] if p == 'Fascist']) >= 5:
            # Give the Chancellor the option to veto
            president = user_cache[session['president']]
            chancellor = user_cache[session['chancellor']]
            view = VetoView(self.ctx, self.select.selected_policy,
                            president, chancellor, session, channel)
            await interaction.response.send_message(f"{interaction.user.mention}, you may veto this agenda if the President agrees.", view=view)

        else:
            if session['state'] != 'policy_enactment' or interaction.user.id != session['chancellor']:
                await interaction.response.send_message("You cannot enact policies at this time.", ephemeral=True)
                return

            # Extract the policy name from the selected value
            policy = self.select.selected_policy

            if policy not in session['policies_drawn']:
                await interaction.response.send_message("Invalid policy selected.", ephemeral=True)
                return

            # Enact the policy and reset for the next round
            enacted_policy = policy
            stats[interaction.user.id]['policies_enacted'][enacted_policy] += 1
            session.get('policies', []).remove(enacted_policy)
            await interaction.response.defer()
            await interaction.followup.send(
                f"You have enacted the **{enacted_policy}** policy!  Head over to {channel.mention}")
            if enacted_policy == 'Fascist':
                color = discord.Color.red()
            elif enacted_policy == 'Liberal':
                color = discord.Color.blue()
            elif enacted_policy == 'Communist':
                color = 0xff0000
            elif enacted_policy == 'Anarchist':
                color = 0x000000
            elif enacted_policy.startswith("Anti"):
                color = discord.Color.darker_grey()
            embed = discord.Embed(
                title="Policy Enacted",
                description=f"A **{enacted_policy}** Policy has been enacted.",
                color=color
            )
            policy_card = f"GameAssets/{enacted_policy} Article.png"
            if os.path.isfile(policy_card):
                file = discord.File(policy_card, filename="policy.png")
                embed.set_image(url="attachment://policy.png")
                await channel.send(embed=embed, file=file)

            # Disable the dropdown after selection
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            await self.handle_policy_enactment()

    async def handle_policy_enactment(self):
        global user_cache
        enacted_policy = self.select.selected_policy
        try:
            if enacted_policy == "Anti Communist":
                # remove if it exists, otherwise ignore:
                if 'Communist' in session['enacted_policies']:
                    session['enacted_policies'].remove('Communist')
                session['enacted_policies'].append('Fascist')
            elif enacted_policy == 'Anti Fascist':
                # remove if it exists, otherwise ignore:
                if 'Fascist' in session['enacted_policies']:
                    session['enacted_policies'].remove('Fascist')
                session['enacted_policies'].append('Communist')
            else:
                session['enacted_policies'].append(enacted_policy)
        except KeyError:
            if enacted_policy == "Anti Communist":
                session['enacted_policies'] = ['Fascist']
            elif enacted_policy == 'Anti Fascist':

                session['enacted_policies'] = ['Communist']
            else:
                session['enacted_policies'] = [enacted_policy]
        policies_remaining = session['policies_drawn']
        if enacted_policy:
            policies_remaining.remove(enacted_policy)
            session['discard_pile'].extend(policies_remaining)
            for policy in policies_remaining:
                session.get('policies', []).remove(policy)

        # Check for game end conditions
        fasc_count = sum(
            1 for p in session['enacted_policies'] if p == 'Fascist')
        lib_count = sum(
            1 for p in session['enacted_policies'] if p == 'Liberal')
        comm_count = sum(
            1 for p in session['enacted_policies'] if p == 'Communist')
        anar_count = sum(
            1 for p in session['enacted_policies'] if p == 'Anarchist')
        fasc_tracker = f"GameAssets/Fascist Tracker {fasc_count}.png"
        lib_tracker = f"GameAssets/Liberal Tracker {
            session['election_tracker']}-{lib_count}.png"
        comm_tracker = f"GameAssets/Communist Tracker {
            comm_count+anar_count}-{anar_count}.png"
        if os.path.isfile(fasc_tracker):
            file = discord.File(fasc_tracker, filename="fasctracker.png")
            await channel.send(file=file)
        if os.path.isfile(lib_tracker):
            file = discord.File(lib_tracker, filename="libtracker.png")
            await channel.send(file=file)
        if os.path.isfile(comm_tracker) and session.get('mode', 'Normal') == 'XL':
            file = discord.File(comm_tracker, filename="commtracker.png")
            await channel.send(file=file)
        powers = ['investigate_loyalty',
                  'call_special_election', 'policy_peek', 'execution']
        # check number of policies employed that are fascist:
        session['last_government'] = {
            'president': session['president'], 'chancellor': session['chancellor']}

        # Determine the executive action based on the number of players and policies
        if await check_win(self.ctx, session, channel):
            if enacted_policy in ['Fascist', 'Anti Communist']:
                session['executive_action'] = ""
                if len(session['players']) >= 9:
                    if fasc_count == 1:
                        session['executive_action'] = powers[0]
                    elif fasc_count == 2:
                        session['executive_action'] = powers[0]
                    elif fasc_count == 3:
                        session['executive_action'] = powers[1]
                    elif fasc_count >= 4:
                        session['executive_action'] = powers[3]
                elif len(session['players']) in [7, 8]:
                    if fasc_count == 2:
                        session['executive_action'] = powers[0]
                    elif fasc_count == 3:
                        session['executive_action'] = powers[1]
                    elif fasc_count >= 4:
                        session['executive_action'] = powers[3]
                elif len(session['players']) <= 6:
                    if fasc_count == 3:
                        session['executive_action'] = powers[2]
                    elif fasc_count >= 4:
                        session['executive_action'] = powers[3]
                await handle_executive_action(self.ctx, session, channel)
            elif enacted_policy in ['Communist', 'Anti Fascist']:
                session['communist_action'] = ""
                # #test
                # if len(session['players']) <= 4:
                #     session['communist_action'] = "bugging"
                if comm_count + anar_count == 1:
                    session['communist_action'] = "bugging"
                elif comm_count + anar_count == 2:
                    session['communist_action'] = "radicalization"
                elif comm_count + anar_count == 3:
                    session['communist_action'] = "five_year_plan"
                elif comm_count + anar_count == 4:
                    session['communist_action'] = "congress"
                elif comm_count + anar_count == 5:
                    session['communist_action'] = 'confession'
                await handle_communist_power(self.ctx, session, channel)
            else:
                session['state'] = 'new_round'
                session['pressed_button'] = False
                president = user_cache[session['president']]
                view = PropagandaView(
                    self.ctx, session['policies'], session, channel)
                if session.get('mode', 'Normal') == 'XL' and not session.get('propaganda', False):
                    await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

                await asyncio.sleep(10)
                if session['state'] == 'new_round' and not session.get('pressed_button', False):
                    embed = discord.Embed(
                        title="End of Term",
                        description=f"President {
                            president.mention}, your term is ending. Click the button below to proceed.",
                        color=discord.Color.blue()
                    )
                    # Add the button to end the term
                    view = EndTermView(session, self.ctx, channel)
                    await channel.send(embed=embed, view=view)

                    save_game_state()


class PropagandaDecisionView(View):
    def __init__(self, ctx, top_policy, session, channel):
        super().__init__()
        self.ctx = ctx
        self.session = session
        self.channel = channel
        self.top_policy = top_policy

    @discord.ui.button(label="Keep", style=discord.ButtonStyle.green)
    async def keep_policy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You have chosen to keep the policy.", ephemeral=True)
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Discard", style=discord.ButtonStyle.red)
    async def discard_policy_propaganda(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message("You have chosen to discard the policy.", ephemeral=True)
        self.session['discard_pile'].extend([self.top_policy])
        self.session.get('policies', []).remove(self.top_policy)
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)


class PropagandaView(View):
    def __init__(self, ctx, policies, session, channel):
        super().__init__()
        self.ctx = ctx
        self.session = session
        self.channel = channel

    @discord.ui.button(label="Illicit Propaganda", style=discord.ButtonStyle.green)
    async def enact_illicit_propaganda(self, interaction: discord.Interaction, button: discord.ui.Button):
        global user_cache
        # check  the top card and give option to discard or keep itL:
        if interaction.user.id != self.session['president']:
            await interaction.response.send_message("Only the President can use Propaganda.", ephemeral=True)
            return
        top_policy = self.session.get('policies', [])[0]
        view = PropagandaDecisionView(
            self.ctx, top_policy, self.session, self.channel)
        await interaction.message.edit(content=f"The top policy is {top_policy}. Do you want to keep it or discard it?", view=view)
        article_48_embed = discord.Embed(
            title="Article 48 has been enacted!",
            description=f"# The President has looked at the top policy in the deck.",
            color=0xffffff
        )
        article_48 = "GameAssets/Article 48.png"
        if os.path.isfile(article_48):
            file = discord.File(article_48, filename="article48.png")
            article_48_embed.set_image(url="attachment://article48.png")
            await self.channel.send(embed=article_48_embed, file=file)
        self.session['propaganda'] = True

    @discord.ui.button(label="Reject Propaganda", style=discord.ButtonStyle.green)
    async def reject_propaganda(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.session['president']:
            await interaction.response.send_message("Only the President can use Propaganda.", ephemeral=True)
            return
        await interaction.response.send_message("You have chosen to reject the propaganda.", ephemeral=True)
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)


class VoteOfNoConfidenceView(View):
    def __init__(self, ctx, voteview, votemsg, session, channel):
        super().__init__()
        self.ctx = ctx
        self.session = session
        self.channel = channel
        self.voteview = voteview
        self.votemsg = votemsg

    @discord.ui.button(label="Initiate No Confidence", style=discord.ButtonStyle.green)
    async def enact_no_confidence(self, interaction: discord.Interaction, button: discord.ui.Button):
        global user_cache
        if interaction.user.id != self.session['chancellor']:
            await interaction.response.send_message("Only the Chancellor can enact a Vote of No Confidence.", ephemeral=True)
            return
        if self.session.get('vote_of_no_confidence_used', False):
            await interaction.response.send_message("Vote of No Confidence has already been used.", ephemeral=True)
            return

        # Enact the President's discarded policy instead of the two sent policies
        enacted_policy = self.session['discard_pile'][-1]
        self.session['discard_pile'] = self.session['discard_pile'][:-1]
        chl = await bot.fetch_channel(self.channel)
        await interaction.response.send_message(f"The Vote of No Confidence was successful. The discarded policy {enacted_policy} has been enacted.")
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        for it in self.voteview.children:
            it.disabled = True
        await self.votemsg.edit(view=self.voteview)
        enabling_act_embed = discord.Embed(
            title="An Enabling Act has been enacted!",
            description=f"# The Chancellor has initiated the VOTE OF NO CONFIDENCE. The policy discarded by the President has been enacted.",
            color=0xffffff
        )
        enabling_act = "GameAssets/Enabling Act.png"
        if os.path.isfile(enabling_act):
            file = discord.File(enabling_act, filename="enablingact.png")
            enabling_act_embed.set_image(url="attachment://enablingact.png")
            await chl.send(embed=enabling_act_embed, file=file)
        # Mark Vote of No Confidence as used
        if 'vnoc_result' not in self.session:
            self.session['vonc_enacted'] = True
        self.session['vonc'] = False
        policy_card = f"GameAssets/{enacted_policy} Article.png"
        if enacted_policy == 'Fascist':
            color = discord.Color.red()
        elif enacted_policy == 'Liberal':
            color = discord.Color.blue()
        elif enacted_policy == 'Communist':
            color = 0xff0000
        elif enacted_policy == 'Anarchist':
            color = 0x000000
        elif enacted_policy.startswith("Anti"):
            color = discord.Color.darker_grey()
        embed = discord.Embed(
            title="Policy Enacted",
            description=f"A **{enacted_policy}** Policy has been enacted.",
            color=color
        )
        if os.path.isfile(policy_card):
            file = discord.File(policy_card, filename="policy.png")
            embed.set_image(url="attachment://policy.png")
            await chl.send(embed=embed, file=file)
        try:
            if enacted_policy == "Anti Communist":
                # remove if it exists, otherwise ignore:
                if 'Communist' in self.session['enacted_policies']:
                    self.session['enacted_policies'].remove('Communist')
                self.session['enacted_policies'].append('Fascist')
            elif enacted_policy == 'Anti Fascist':
                # remove if it exists, otherwise ignore:
                if 'Fascist' in self.session['enacted_policies']:
                    self.session['enacted_policies'].remove('Fascist')
                self.session['enacted_policies'].append('Communist')
            else:
                self.session['enacted_policies'].append(enacted_policy)
        except KeyError:
            if enacted_policy == "Anti Communist":
                self.session['enacted_policies'] = ['Fascist']
            elif enacted_policy == 'Anti Fascist':

                self.session['enacted_policies'] = ['Communist']
            else:
                self.session['enacted_policies'] = [enacted_policy]
        policies_remaining = self.session['policies_drawn']
        if enacted_policy:
            self.session['discard_pile'].extend(policies_remaining)
            for policy in policies_remaining:
                self.session.get('policies', []).remove(policy)

        # Check for game end conditions
        fasc_count = sum(
            1 for p in self.session['enacted_policies'] if p == 'Fascist')
        lib_count = sum(
            1 for p in self.session['enacted_policies'] if p == 'Liberal')
        comm_count = sum(
            1 for p in self.session['enacted_policies'] if p == 'Communist')
        anar_count = sum(
            1 for p in self.session['enacted_policies'] if p == 'Anarchist')
        fasc_tracker = f"GameAssets/Fascist Tracker {fasc_count}.png"
        lib_tracker = f"GameAssets/Liberal Tracker {
            self.session['election_tracker']}-{lib_count}.png"
        comm_tracker = f"GameAssets/Communist Tracker {
            comm_count+anar_count}-{anar_count}.png"
        if os.path.isfile(fasc_tracker):
            file = discord.File(fasc_tracker, filename="fasctracker.png")
            await chl.send(file=file)
        if os.path.isfile(lib_tracker):
            file = discord.File(lib_tracker, filename="libtracker.png")
            await chl.send(file=file)
        if os.path.isfile(comm_tracker) and session.get('mode', 'Normal') == 'XL':
            file = discord.File(comm_tracker, filename="commtracker.png")
            await chl.send(file=file)
        powers = ['investigate_loyalty',
                  'call_special_election', 'policy_peek', 'execution']
        # check number of policies employed that are fascist:
        self.session['last_government'] = {
            'president': self.session['president'], 'chancellor': self.session['chancellor']}

        # Determine the executive action based on the number of players and policies
        if await check_win(self.ctx, self.session, channel):
            if enacted_policy in ['Fascist', 'Anti Communist']:
                self.session['executive_action'] = ""
                if len(self.session['players']) >= 9:
                    if fasc_count == 1:
                        self.session['executive_action'] = powers[0]
                    elif fasc_count == 2:
                        self.session['executive_action'] = powers[0]
                    elif fasc_count == 3:
                        self.session['executive_action'] = powers[1]
                    elif fasc_count >= 4:
                        self.session['executive_action'] = powers[3]
                elif len(self.session['players']) in [7, 8]:
                    if fasc_count == 2:
                        self.session['executive_action'] = powers[0]
                    elif fasc_count == 3:
                        self.session['executive_action'] = powers[1]
                    elif fasc_count >= 4:
                        self.session['executive_action'] = powers[3]
                elif len(self.session['players']) <= 6:
                    if fasc_count == 3:
                        self.session['executive_action'] = powers[2]
                    elif fasc_count >= 4:
                        self.session['executive_action'] = powers[3]
                await handle_executive_action(self.ctx, self.session, channel)
            elif enacted_policy in ['Communist', 'Anti Fascist']:
                self.session['communist_action'] = ""
                # #test
                # if len(self.session['players']) <= 4:
                #     self.session['communist_action'] = "bugging"
                if comm_count + anar_count == 1:
                    self.session['communist_action'] = "bugging"
                elif comm_count + anar_count == 2:
                    self.session['communist_action'] = "radicalization"
                elif comm_count + anar_count == 3:
                    self.session['communist_action'] = "five_year_plan"
                elif comm_count + anar_count == 4:
                    self.session['communist_action'] = "congress"
                elif comm_count + anar_count == 5:
                    self.session['communist_action'] = 'confession'
                await handle_communist_power(self.ctx, self.session, channel)
            else:
                self.session['state'] = 'new_round'
                self.session['pressed_button'] = False
                president = user_cache[self.session['president']]
                view = PropagandaView(
                    self.ctx, self.session['policies'], self.session, self.channel)
                if session.get('mode', 'Normal') == 'XL' and not session.get('propaganda', False):
                    await president.send("You have the option to enact Illicit Propaganda or Reject Propaganda.", view=view)

                await asyncio.sleep(10)
                if self.session['state'] == 'new_round' and not self.session.get('pressed_button', False):
                    embed = discord.Embed(
                        title="End of Term",
                        description=f"President {
                            president.mention}, your term is ending. Click the button below to proceed.",
                        color=discord.Color.blue()
                    )
                    # Add the button to end the term
                    view = EndTermView(self.session, self.ctx, channel)
                    await channel.send(embed=embed, view=view)

                    save_game_state()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.session['chancellor']:
            await interaction.response.send_message("Only the Chancellor can enact a Vote of No Confidence.", ephemeral=True)
            return
        await interaction.response.send_message("You have cancelled the Vote of No Confidence.", ephemeral=True)
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        if 'vonc_enacted' not in session:
            session['vonc_enacted'] = True
        save_game_state()


async def enact_policy(ctx, session, channel):
    global user_cache
    global enacted_policy
    chancellor = user_cache[session['chancellor']]

    # Chancellor receives 2 remaining policies
    policies_remaining = session['policies_drawn']

    # Create and send the dropdown
    view = EnactPolicyView(ctx, policies_remaining)
    votemsg = await chancellor.send(f"{chancellor.mention}, please select a policy to enact from the dropdown below:", view=view)
    if session.get('vonc', False):
        voncview = VoteOfNoConfidenceView(ctx, view, votemsg, session, channel)
        await chancellor.send(f"{chancellor.mention}, you may call a Vote of No Confidence if you wish. This will enact the policy that the president discarded.", view=voncview)
    session['state'] = 'policy_enactment'
    save_game_state()


async def start_next_round(ctx, session, channel):
    # Rotate the President to the next player
    players = session['players']
    if session.get('special_election', False):
        session['special_election'] = False
        session['president'] = session['prev_president']
    current_president_index = players.index(session['president'])
    next_president_index = (current_president_index + 1) % len(players)
    session['president'] = players[next_president_index]

    # Clear the previous chancellor and chancellor candidate
    session['chancellor'] = None
    session['chancellor_candidate'] = None

    # Move back to the election phase
    await start_election_round(ctx, session, channel)

# command to end term:


@bot.hybrid_command(name="end_term", description="End the current Presidential term")
async def end_term(ctx: commands.Context):
    global channel
    if ctx.author.id == session['president']:
        if session['state'] == 'new_round':
            embed = discord.Embed(
                title="Presidential Term Ended",
                description="The current Presidential term has ended.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            await start_next_round(ctx, session, channel)
        else:
            await ctx.send("You cannot end the term at this time.", ephemeral=True)
    else:
        await ctx.send("Only the current President can end the term.", ephemeral=True)


@bot.hybrid_command(name="terminate_game", description="End the current Secret Hitler game session")
@commands.has_permissions(administrator=True)
async def terminate_game(ctx: commands.Context, winner: str = None):
    global user_cache
    global channel, session, stats
    if ctx:
        guild_id = ctx.guild.id
        if guild_id not in game_sessions:
            embed = discord.Embed(
                title="No Game in Progress",
                description="There is no game in progress to end.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        else:
            session = game_sessions[guild_id]
        save_game_state()

        embed = discord.Embed(
            title="Game Ended",
            description="The current game session has been terminated.",
            color=discord.Color.red()
        )
        # delete channel:
        await ctx.send(embed=embed)
        # put comma seperated winners into a list:
        if winner:
            winner = [w.strip() for w in winner.split(',')]

    if ctx == None and session == None:
        session = game_sessions[channel.guild.id]
    if winner == None:
        winner = []
    corresponding_role = ""
    for player in session['players']:
        if str(player) not in stats:
            await initialize_player_stats(str(player))
        if winner != []:
            if session['roles'][player] in winner:
                stats[str(player)]['wins'] += 1
                stats[str(player)][f'win_as_{session['roles'][player]}'] += 1
                stats[str(player)]['games'] += 1
            else:
                stats[str(player)]['losses'] += 1
                stats[str(player)][f'loss_as_{session['roles'][player]}'] += 1
                stats[str(player)]['games'] += 1
        # user = user_cache[player)
        corresponding_role += f"**<@{player}>: {session['roles'][player]}** - {
            "Won" if session['roles'][player] in winner else "Lost"}\n"
    dead = session.get('executed_players', [])
    for player in dead:
        if not stats[str(player)]:
            await initialize_player_stats(str(player))
        if winner != []:
            if session['roles'][player] in winner:
                stats[str(player)]['wins'] += 1
                stats[str(player)][f'win_as_{session['roles'][player]}'] += 1
                stats[str(player)]['games'] += 1
            else:
                stats[str(player)]['losses'] += 1
                stats[str(player)][f'loss_as_{session['roles'][player]}'] += 1
                stats[str(player)]['games'] += 1
        corresponding_role += f'''**<@{player}>: {
            session['roles'][player]}** :skull_crossbones: - {"Won" if session['roles'][player] in winner else "Lost"}\n'''
    if session.get('mode', 'Normal') == 'XL':
        if "Fascist" in winner:
            desc = f"**{', '.join(winner)}** Win!"
            color = discord.Color.orange()
            img = f"GameAssets/{' '.join(winner)} Win.png"
        elif "Liberal" in winner:
            desc = f"**{', '.join(winner)}** Win!"
            color = discord.Color.blue()
            img = f"GameAssets/{' '.join(winner)} Win.png"
        elif "Communist" in winner:
            desc = f"**{', '.join(winner)}** Win!"
            color = 0xff0000
            img = f"GameAssets/{' '.join(winner)} Win.png"
        elif "Anarchist" in winner:
            desc = f"**{', '.join(winner)}** Win!"
            color = 0x000000
            img = f"GameAssets/{' '.join(winner)} Win.png"
        else:
            desc = "Game Terminated"
            color = discord.Color.red()
            img = "GameAssets/Banner.png"
    else:
        if "Fascist" in winner:
            desc = f"**Fascists** Win!"
            color = discord.Color.orange()
            img = f"GameAssets/Fascist Win.png"
        elif "Liberal" in winner:
            desc = f"**Liberals** Win!"
            color = discord.Color.blue()
            img = f"GameAssets/Liberal Win.png"
        else:
            desc = "Game Terminated"
            color = discord.Color.red()
            img = "GameAssets/Banner.png"
    final_embed = discord.Embed(
        title="Game Ended",
        description=desc,
        color=color
    )
    final_embed.add_field(name="Roles", value=corresponding_role)
    initchannel = session['init_channel']
    initchannel = await bot.fetch_channel(initchannel)
    thumbnail = "GameAssets/Game End.png"
    # set img as image and thumbnail as thumbnail of embed"
    files = []
    if os.path.isfile(img):
        file = discord.File(img, filename="gameend.png")
        files.append(file)
        final_embed.set_image(url="attachment://gameend.png")
    if os.path.isfile(thumbnail):
        file = discord.File(thumbnail, filename="thumbnail.png")
        files.append(file)
        final_embed.set_thumbnail(url="attachment://thumbnail.png")
    await initchannel.send(embed=final_embed, files=files)
    fascist_tracker = discord.Embed(
        title="Fascist Card Tracker",
        color=discord.Color.red()
    )
    liberal_tracker = discord.Embed(
        title="Liberal Card Tracker",
        color=discord.Color.blue()
    )
    communist_tracker = discord.Embed(
        title="Communist Card Tracker",
        color=0xff0000
    )
    fasc_count = sum(
        1 for p in session['enacted_policies'] if p == 'Fascist')
    lib_count = sum(
        1 for p in session['enacted_policies'] if p == 'Liberal')
    comm_count = sum(
        1 for p in session['enacted_policies'] if p == 'Communist')
    anar_count = sum(
        1 for p in session['enacted_policies'] if p == 'Anarchist')
    fasc_tracker = f"GameAssets/Fascist Tracker {fasc_count}.png"
    lib_tracker = f"GameAssets/Liberal Tracker {
        session['election_tracker']}-{lib_count}.png"
    comm_tracker = f"GameAssets/Communist Tracker {
        comm_count+anar_count}-{anar_count}.png"
    if os.path.isfile(fasc_tracker):
        file = discord.File(fasc_tracker, filename="fasctracker.png")
        fascist_tracker.set_image(url="attachment://fasctracker.png")
        await initchannel.send(embed=fascist_tracker, file=file)
    if os.path.isfile(lib_tracker):
        file = discord.File(lib_tracker, filename="libtracker.png")
        liberal_tracker.set_image(url="attachment://libtracker.png")
        await initchannel.send(embed=liberal_tracker, file=file)
    if os.path.isfile(comm_tracker) and session.get('mode', 'Normal') == 'XL':
        file = discord.File(comm_tracker, filename="commtracker.png")
        communist_tracker.set_image(url="attachment://commtracker.png")
        await initchannel.send(embed=communist_tracker, file=file)
    session['players'].extend(session.get('executed_players', []))
    session['players'].extend(session['queue'])
    players = session['players']
    session['queue'] = []
    player_list = ""
    for i, player in enumerate(players):
        player_object = user_cache[player]
        player_list += f"{i+1}. **{player_object.display_name}**" + "\n"

    embed = discord.Embed(
        title="Current Game Lobby",
        description=f"Players in the lobby:\n{player_list}",
        color=discord.Color.blue()
    )

    await initchannel.send(embed=embed)
    await asyncio.sleep(5)
    channel = session.get('channel_id', None)

    channel = await bot.fetch_channel(channel)
    if channel:
        await channel.delete()
    guild_id = channel.guild.id

    mode = session['mode']
    # Clear all other session data
    game_sessions[guild_id] = {
        'players': players,  # Retain the players who were in the game
        'roles': {},
        'state': 'waiting',  # Set the state to 'waiting' for a new game
        'running': False,
        'queue': [],
        'initchannel': initchannel.id,
        'mode': mode,
        'communism': False
    }
    with open('stats_xl.json', 'w') as f:
        json.dump(stats, f, indent=4)
    save_game_state()

# Load the .env file
dotenv.load_dotenv()
bot.run(os.getenv('TOKEN'))
