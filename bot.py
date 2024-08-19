import random
import dotenv
import discord
from discord.ext import commands
import pickle
import os

# Set up the bot
intents = discord.Intents.default()
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



@bot.event
async def on_ready():
    global game_sessions
    print(f'We have logged in as {bot.user}')
    await bot.tree.sync()
    game_sessions = load_game_state()
# Hybrid command to start a new game session
@bot.hybrid_command(name="start_game", description="Start a new Secret Palpatine game session")
async def start_game(ctx: commands.Context):
    guild_id = ctx.guild.id
    if guild_id in game_sessions:
        embed = discord.Embed(
            title="Game Already in Progress",
            description="A game is already in progress in this server. Please wait for it to finish or use `!end_game` to terminate the current session.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Initialize the game session
    game_sessions[guild_id] = {
        'players': [],
        'roles': {},
        'state': 'waiting'
    }
    save_game_state()

    embed = discord.Embed(
        title="New Game Session Started",
        description="A new game session has been started! Players can join using `!join_game`.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# Hybrid command for players to join the game


@bot.hybrid_command(name="join_game", description="Join the Secret Palpatine game")
async def join_game(ctx: commands.Context):
    guild_id = ctx.guild.id
    if guild_id not in game_sessions or game_sessions[guild_id]['state'] != 'waiting':
        embed = discord.Embed(
            title="No Game Session Available",
            description="There is no game session available to join. Please wait for the host to start a new game.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    player = ctx.author
    if player.id in game_sessions[guild_id]['players']:
        embed = discord.Embed(
            title="Already Joined",
            description="You have already joined the game.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    game_sessions[guild_id]['players'].append(player.id)
    save_game_state()

    embed = discord.Embed(
        title="Player Joined",
        description=f"{player.name} has joined the game!",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

    # Send a private confirmation message to the player
    await player.send(embed=discord.Embed(
        title="Welcome to the Game!",
        description="You have joined the Secret Palpatine game. Get ready!",
        color=discord.Color.green()
    ))

# Hybrid command to start the game once all players have joined


@bot.hybrid_command(name="begin_game", description="Begin the Secret Palpatine game")
async def begin_game(ctx: commands.Context):
    guild_id = ctx.guild.id
    session = game_sessions.get(guild_id)

    if not session or session['state'] != 'waiting':
        embed = discord.Embed(
            title="No Game Ready to Begin",
            description="There is no game session ready to begin. Please start a game with `!start_game`.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    player_count = len(session['players'])

    if player_count < 5:
        embed = discord.Embed(
            title="Not Enough Players",
            description="Not enough players to start the game. A minimum of 5 players is required.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    # Algorithmically calculate the number of Fascists
    # At least 1 Fascist, roughly 1 per 3 players
    fascists_count = max(1, (player_count // 3))
    liberals_count = player_count - fascists_count - \
        1  # Remaining players are Liberals
    roles = ['Liberal'] * liberals_count + \
        ['Fascist'] * fascists_count + ['Palpatine']

    # Shuffle players and assign roles randomly
    random.shuffle(session['players'])
    session['roles'] = {session['players'][i]: roles[i]
                        for i in range(player_count)}

    # Assign a random player as the initial President
    president_id = random.choice(session['players'])
    session['president'] = president_id

    # Notify players of their roles via DM
    for player_id in session['players']:
        player = await bot.fetch_user(player_id)
        role = session['roles'][player_id]
        message = f"Your role is: **{role}**."
        if player_id == president_id:
            message += "\nYou are the **President**."

        await player.send(embed=discord.Embed(
            title="Your Role in the Game",
            description=message,
            color=discord.Color.purple()
        ))

    session['state'] = 'in_progress'
    save_game_state()

    embed = discord.Embed(
        title="Game Started",
        description=f"The game has started with {
            player_count} players! Check your DMs for your role.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


# Hybrid command to end the game (for moderators)


@bot.hybrid_command(name="end_game", description="End the current Secret Palpatine game session")
@commands.has_permissions(administrator=True)
async def end_game(ctx: commands.Context):
    guild_id = ctx.guild.id
    if guild_id not in game_sessions:
        embed = discord.Embed(
            title="No Game in Progress",
            description="There is no game in progress to end.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    del game_sessions[guild_id]
    save_game_state()

    embed = discord.Embed(
        title="Game Ended",
        description="The current game session has been terminated.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)
# Load the bot with your token

# Load the .env file
dotenv.load_dotenv()
bot.run(os.getenv('TOKEN'))
