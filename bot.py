import asyncio
import random
import dotenv
import discord
from discord import app_commands
from discord.ui import Button, View, Select
from discord.ext import commands, tasks
import pickle
import os

POLICIES = ['Liberal'] * 6 + ['Fascist'] * 11
random.shuffle(POLICIES)
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



@bot.event
async def on_ready():
    global game_sessions
    print(f'We have logged in as {bot.user}')
    await bot.tree.sync()
    game_sessions = load_game_state()
# Hybrid command to start a new game session
@bot.hybrid_command(name="start_game", description="Start a new Secret Hitler game session")
async def start_game(ctx: commands.Context):
    global game_sessions
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


@bot.hybrid_command(name="join_game", description="Join the Secret Hitler game")
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


# Hybrid command to start the game once all players have joined


@bot.hybrid_command(name="begin_game", description="Begin the Secret Hitler game")
async def begin_game(ctx: commands.Context):
    global session, channel
    await ctx.defer()
    guild = ctx.guild
    guild_id = guild.id
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

    if player_count < 1:
        embed = discord.Embed(
            title="Not Enough Players",
            description="Not enough players to start the game. A minimum of 5 players is required.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    # Role Assignment
    fascists_count = max(1, (player_count // 3))
    liberals_count = player_count - fascists_count - 1
    roles = ['Liberal'] * liberals_count + \
        ['Fascist'] * fascists_count + ['Hitler']

    random.shuffle(session['players'])
    session['roles'] = {session['players'][i]: roles[i]
                        for i in range(player_count)}

    president_id = session['players'][0]  # First player starts as President
    session['president'] = president_id

    # Create a new text channel for the game
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    #all the participants should be able to view and type in the channel"
    for player_id in session['players']:
        player = await bot.fetch_user(player_id)
        #dm the rhe role as an embed:
        role = session['roles'][player_id]
        if role == 'Liberal':
            color = discord.Color.blue()
            desc = "You are a **Liberal**.\n\n# GOAL\n Your goal is to protect the future of the country by enacting five Liberal Policies or by finding and killing Hitler. Stay vigilant, as the Fascists will try to deceive and manipulate the government for their nefarious purposes. Trust your instincts and your fellow Liberals, but be cautious—anyone could be a hidden Fascist or, worse, Hitler."
        elif role == 'Hitler':
            color = discord.Color.red()
            desc = "You are **Hitler**.\n\n# GOAL\n Although you are part of the Fascist team, you must act like a Liberal to avoid suspicion. Your identity is known only to the Fascists. Work with them subtly to advance Fascist policies without revealing yourself. Victory is yours if you are elected Chancellor after three Fascist Policies have been enacted. Be careful—if the Liberals discover your identity, they will stop at nothing to assassinate you."
        else:
            color = discord.Color.orange()
            desc = "You are a **Fascist**.\n\n# GOAL\n Your mission is to undermine the Liberal government and pave the way for Hitler to rise to power. Work in secret to sow discord and enact six Fascist Policies. Be careful, as you must avoid detection. Your ultimate goal is to ensure Hitler's election as Chancellor after three Fascist Policies have been enacted."
        await player.send(embed=discord.Embed(
            title=f"Your Role: **{role}**",
            description=desc,
            color=color
        ))
        overwrites[player] = discord.PermissionOverwrite(
            read_messages=True, send_messages
            =True)  

    channel = await guild.create_text_channel('secret-Hitler', overwrites=overwrites)
    session['channel_id'] = channel.id

    # Ping all players in the channel
    mentions = ', '.join(
        [f'<@{player_id}>' for player_id in session['players']])
    chl = await bot.fetch_channel(channel.id)
    await ctx.send(f"Game starting! Head over to {chl.mention}")
    await channel.send(f"Game has started! Players: {mentions}")

    # Announce the first President
    president = president_id
    session['president'] = president
    #await channel.send(f"The first President is {president.mention}!")
    save_game_state()
    # Start the first election round
    await start_election_round(ctx, session, channel)


class ChancellorSelect(Select):
    def __init__(self, ctx, players):
        self.ctx = ctx
        options = [discord.SelectOption(
            label=user.display_name, value=user.id) for user in players]
        super().__init__(placeholder="Select a Chancellor...",
                         min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Handle the selected chancellor
        global session
        selected_chancellor_id = int(self.values[0])
        session['chancellor'] = selected_chancellor_id
        save_game_state()
        chancellor = await bot.fetch_user(selected_chancellor_id)
        chl = await bot.fetch_channel(session['channel_id'])
        await interaction.response.send_message(f"You have chosen a Chancellor. Return to {chl.mention}")
        await start_vote(self.ctx, session['channel_id'], interaction.user , chancellor)

async def start_election_round(ctx, session, channel):
    guild_id = ctx.guild.id
    president_id = session['president']
    players = []
    for member in ctx.guild.members:
        if member.id in session['players']:
            players.append(member)
    # Announce the start of the election round
    embed = discord.Embed(
        title="Election Phase",
        description=f"<@{president_id}> is now the Presidential Candidate. Please choose a Chancellor in your DM.",
        color=discord.Color.blue()
    )
    await channel.send(embed=embed)

    # Create and send the dropdown
    select = ChancellorSelect(ctx, players)
    view = View()
    view.add_item(select)
    session['state'] = 'chancellor_nomination'
    save_game_state()
    #send the dm to the president. Find president using the president_id:
    pres = await bot.fetch_user(president_id)
    await pres.send(f"{pres.mention}, please nominate a Chancellor by selecting from the dropdown below:", view=view)

    # Move to the Chancellor nomination phase
    
    


@bot.hybrid_command(name="nominate", description="Nominate a Chancellor candidate")
@app_commands.describe(chancellor="The player to nominate as Chancellor")
async def nominate_chancellor(ctx: commands.Context, chancellor: discord.Member):
    guild_id = ctx.guild.id
    session = game_sessions.get(guild_id)

    if session['state'] != 'chancellor_nomination' or ctx.author.id != session['president']:
        await ctx.send("You cannot nominate a Chancellor at this time.", ephemeral=True)
        return

    chancellor_id = chancellor.id

    # Check eligibility
    last_government = session.get('last_government', {})
    if chancellor_id == last_government.get('president') or (len(session['players']) > 5 and chancellor_id == last_government.get('chancellor')):
        await ctx.send(f"{chancellor.mention} is ineligible to be Chancellor this round.", ephemeral=True)
        return

    # Proceed with the nomination
    session['chancellor_candidate'] = chancellor_id
    save_game_state()

    # Announce the nomination and start the vote
    await start_vote(ctx, session['channel_id'], ctx.author, chancellor)


async def start_vote(ctx, channel_id, president, chancellor):
    channel = bot.get_channel(channel_id)
    if not channel:
        return
    embed = discord.Embed(
        title="Vote on the Government",
        description=f"{president.mention} has nominated {
            chancellor.mention} as Chancellor. Please vote!",
        color=discord.Color.green()
    )

    view = ChancellorVoteView(session, session['players'], ctx)
    await channel.send(embed=embed, view=view)


class ChancellorVoteView(View):
    def __init__(self,session, players, ctx):
        super().__init__()
        self.players = players
        self.votes = {}
        self.ctx = ctx
        self.session = session

    @discord.ui.button(label="Vote Yes", style=discord.ButtonStyle.green)
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You voted Yes!", ephemeral=True)
        await self.handle_vote(interaction.user.id, True)

    @discord.ui.button(label="Vote No", style=discord.ButtonStyle.red)
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You voted No!", ephemeral=True)
        await self.handle_vote(interaction.user.id, False)

    async def handle_vote(self, user_id, vote):
        self.votes[user_id] = vote
        if len(self.votes) == len(self.players):
            await self.evaluate_votes()

    async def evaluate_votes(self):
        yes_votes = sum(self.votes.get(vote, 0)
                        for vote in self.votes)  # Sum of all 'yes' votes
        no_votes = len(self.votes) - yes_votes  # Total votes minus 'yes' votes

        if yes_votes > no_votes:
            # Government is elected
            self.session['state'] = 'legislative_session'
            # Reset election tracker or adjust as needed
            self.session['election_tracker'] = 0

            # Notify about the successful election
            channel = self.session['channel_id']
            president = self.session['president']
            message = f"The government has been elected. Proceeding to the legislative session. <@{president}>, please discard a policy in your DM."
            chl = await bot.fetch_channel(channel)
            await chl.send(message)
            #bot.loop.create_task(self.ctx._get_channel(channel).send((message)))

            # Proceed to the legislative session
            await legislative_session(self.ctx, session, channel)
        else:
            # Election fails, advance the election tracker
            self.session['election_tracker'] += 1
            if self.session['election_tracker'] >= 3:
                # If the tracker reaches a certain number (e.g., 3), enact a special rule (like a policy being enacted)
                # Implement your special rule logic here
                pass

            # Notify about the failed election
            channel = self.session['channel_id']
            message = f"The election has failed. The election tracker is now at {
                self.session['election_tracker']}."
            chl = await bot.fetch_channel(channel)
            await chl.send(message)

            # Proceed to the next election phase
            bot.loop.create_task(self.start_next_election())



class PolicySelect(Select):
    def __init__(self, policies):
        options = [discord.SelectOption(label=policy, value=f"{policy}-{i}") for i, policy in enumerate(policies)]
        super().__init__(placeholder="Select a policy to discard...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        #chl = await bot.fetch_channel(channel.id)
        #get guild id of the channel
        guild_id = channel.guild.id

        session = game_sessions.get(guild_id)

        if session['state'] != 'policy_discard' or interaction.user.id != session['president']:
            await interaction.response.send_message("You cannot discard policies at this time.", ephemeral=True)
            return

        # Extract the policy name from the selected value
        policy = self.values[0].rsplit('-', 1)[0]

        if policy not in session['policies_drawn']:
            await interaction.response.send_message("Invalid policy selected.", ephemeral=True)
            return

        # Remove the selected policy
        POLICIES.append(policy)
        session['policies_drawn'].remove(policy)
        await interaction.response.send_message(f"You have discarded the **{policy}** policy. The remaining policies will be sent to the chancellor.")
        save_game_state()

        # Move to the Chancellor's policy enactment phase
        await enact_policy(interaction, session, session['channel_id'])

async def legislative_session(ctx, session, channel):
    president = await bot.fetch_user(session['president'])
    chancellor = await bot.fetch_user(session['chancellor'])

    # President draws top 3 policies:
    policies_drawn = [POLICIES.pop() for _ in range(min(3, len(POLICIES)))]
    session['policies_drawn'] = policies_drawn

    await president.send(f"You have drawn these policies: {', '.join(policies_drawn)}. Please select one to discard.")

    # Create and send the dropdown
    select = PolicySelect(policies_drawn)
    view = View()
    view.add_item(select)

    await president.send(f"{president.mention}, please select a policy to discard from the dropdown below:", view=view)

    session['state'] = 'policy_discard'
    save_game_state()


class EnactPolicySelect(Select):
    def __init__(self, policies):
        options = [discord.SelectOption(
            label=policy, value=f"{policy}-{i}") for i, policy in enumerate(policies)]
        super().__init__(placeholder="Select a policy to enact...",
                         min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        global enacted_policy
        guild_id = channel.guild.id
        session = game_sessions.get(guild_id)
        print(session['state'], session['chancellor'], interaction.user.id)
        if session['state'] != 'policy_enactment' or interaction.user.id != session['chancellor']:
            await interaction.response.send_message("You cannot enact policies at this time.", ephemeral=True)
            return

        # Extract the policy name from the selected value
        policy = self.values[0].rsplit('-', 1)[0]

        if policy not in session['policies_drawn']:
            await interaction.response.send_message("Invalid policy selected.", ephemeral=True)
            return

        # Enact the policy and reset for the next round
        

        enacted_policy = policy
        try:
            session['enacted_policies'].append(enacted_policy)
        except KeyError:
            session['enacted_policies'] = [enacted_policy]
        policies_remaining = session['policies_drawn']
        if enacted_policy:
            policies_remaining.remove(enacted_policy)
            session['policies_drawn'].remove(enacted_policy)
            POLICIES.append(policies_remaining)

        # Check for game end conditions
        #count number of policies that are 'Fascist':
        fasc_count = 0
        lib_count = 0
        for policy in session['enacted_policies']:
            if policy == 'Fascist':
                fasc_count +=1
            else:
                lib_count += 1
        if enacted_policy == 'Fascist' and fasc_count >= 3:
            if session['roles'][session['chancellor']] == 'Hitler':
                await channel.send("The Chancellor was Hitler! The Fascists win!")
                # End the game
            else:
                await channel.send("The Chancellor is not Hitler. The game continues.")
        save_game_state()

        # Start a new round or check for other conditions
        session['state'] = 'new_round'
        save_game_state()
        # Notify the policy enactment
        await interaction.response.send_message(f"The policy '{enacted_policy}' has been enacted.")


async def enact_policy(ctx, session, channel):
    global enacted_policy
    chancellor = await bot.fetch_user(session['chancellor'])

    # Chancellor receives 2 remaining policies
    policies_remaining = session['policies_drawn']
  
    # Create and send the dropdown
    select = EnactPolicySelect(policies_remaining)
    view = View()
    view.add_item(select)

    await chancellor.send(f"{chancellor.mention}, please select a policy to enact from the dropdown below:", view=view)

    session['state'] = 'policy_enactment'
    save_game_state()



@bot.hybrid_command(name="end_game", description="End the current Secret Hitler game session")
@commands.has_permissions(administrator=True)
async def end_game(ctx: commands.Context):
    global channel
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
    # delete channel:
    await ctx.send(embed=embed)
    await asyncio.sleep(5)
    await channel.delete()
    
# Load the bot with your token

# Load the .env file
dotenv.load_dotenv()
bot.run(os.getenv('TOKEN'))
