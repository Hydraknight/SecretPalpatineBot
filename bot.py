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
    session['guild_id'] = guild_id
    session['init_channel'] = ctx.channel.id
    session['enacted_policies'] = []
    session['election_tracker'] = 0
    session['discard_pile'] = []
    session['last_government'] = {
        'president': None,
        'chancellor': None
    }
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
    random.shuffle(session['players'])
    #get the list of fascists in session['players']:
    fascists = [await bot.fetch_user(player) for player in session['players'] if session['roles'][player]
                == 'Fascist']
    fascists = [fascist.display_name for fascist in fascists]
    hitler = None
    for player in session['players']:
        if session['roles'][player] == 'Hitler':
            hitler = await bot.fetch_user(player)
            break
    

    president_id = session['players'][0]  # First player starts as President
    session['president'] = president_id

    # Create a new text channel for the game
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    # all the participants should be able to view and type in the channel"
    for player_id in session['players']:
        player = await bot.fetch_user(player_id)
        # dm the rhe role as an embed:
        role = session['roles'][player_id]
        if role == 'Liberal':
            color = discord.Color.blue()
            desc = "You are a **Liberal**.\n# GOAL\n Your goal is to protect the future of the country by enacting five Liberal Policies or by finding and killing Hitler. Stay vigilant, as the Fascists will try to deceive and manipulate the government for their nefarious purposes. Trust your instincts and your fellow Liberals, but be cautious—anyone could be a hidden Fascist or, worse, Hitler."
        elif role == 'Hitler':
            color = discord.Color.red()
            desc = f"You are **Hitler**.\n# GOAL\n Although you are part of the Fascist team, you must act like a Liberal to avoid suspicion. Your identity is known only to the Fascists. Work with them subtly to advance Fascist policies without revealing yourself. Victory is yours if you are elected Chancellor after three Fascist Policies have been enacted. Be careful—if the Liberals discover your identity, they will stop at nothing to assassinate you."
        else:
            color = discord.Color.orange()
            desc = f"You are a **Fascist**.\n# GOAL\n Your mission is to undermine the Liberal government and pave the way for Hitler to rise to power. Work in secret to sow discord and enact six Fascist Policies. Be careful, as you must avoid detection. Your ultimate goal is to ensure Hitler's election as Chancellor after three Fascist Policies have been enacted.\n## Fascists:\n **{', '.join(fascists)}**\n## Hitler:\n**{hitler.display_name if hitler else 'No Hitler'}**"
        embed=discord.Embed(
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

    # Ping all players in the channel
    # mentions = ', '.join(
    #     [f'<@{player_id}>' for player_id in session['players']])
    chl = await bot.fetch_channel(channel.id)
    #beatiful embed that game is starting at channel:
    embed = discord.Embed(
        title="Game Starting",
        description=f"Game starting! Head over to {chl.mention} to play Secret Hitler!"
    )
    img = "GameAssets/Banner.png"
    if os.path.isfile(img):
        file = discord.File(img, filename="banner.png")
        embed.set_image(url="attachment://banner.png")
        await ctx.send(embed=embed, file=file)
    order = ''
    for i, mention in enumerate(session['players']):
        order+=f"{i+1}. <@{mention}>\n"
    await channel.send(f"Game has started! Players in order:\n {order}")

    # Announce the first President
    president = president_id
    session['president'] = president
    # await channel.send(f"The first President is {president.mention}!")
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

        # Disable the dropdown after selection
        self.disabled = True
        await interaction.message.edit(view=self.view)

        await start_vote(self.ctx, session['channel_id'], interaction.user, chancellor)


async def start_election_round(ctx, session, channel):
    # Fetch the guild using the stored guild_id
    guild = bot.get_guild(session['guild_id'])
    if guild is None:
        # Handle the case where the guild cannot be found
        await channel.send("Error: Guild not found.")
        return

    president_id = session['president']
    invalid = [session['last_government']['chancellor'],
               session['last_government']['president'], president_id]
    invalid = []
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
    #set president avatar as thumbnail:
    president = await bot.fetch_user(president_id)
    embed.set_thumbnail(url=president.avatar)
    president_image_path = "GameAssets/President.png"
    if os.path.isfile(president_image_path):
        file = discord.File(president_image_path, filename="president.png")
        embed.set_image(url="attachment://president.png")
        await channel.send(embed=embed, file=file)
    

    # Create and send the dropdown
    select = ChancellorSelect(ctx, players)
    view = View()
    view.add_item(select)
    session['state'] = 'chancellor_nomination'
    save_game_state()

    # Send the DM to the president
    pres = await bot.fetch_user(president_id)
    await pres.send(f"{pres.mention}, please nominate a Chancellor by selecting from the dropdown below:", view=view)


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
    embed.set_thumbnail(url=chancellor.avatar)
    chancellor_image_path = "GameAssets/Chancellor.png"
    if os.path.isfile(chancellor_image_path):
        file = discord.File(chancellor_image_path, filename="chancellor.png")
        embed.set_image(url="attachment://chancellor.png")
        view = ChancellorVoteView(session, session['players'], ctx)
        await channel.send(embed=embed, view=view, file=file)


class ChancellorVoteView(View):
    def __init__(self, session, players, ctx):
        super().__init__()
        self.players = players
        self.votes = {}  # Dictionary to store votes, format: {user_id: vote}
        self.ctx = ctx
        self.session = session
        self.vote_message = None  # Store the message object for vote updates
        self.lock = asyncio.Lock()  # Semaphore to ensure single execution

    @discord.ui.button(label="Vote Yes", style=discord.ButtonStyle.green)
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self.lock:
            await self.handle_vote(interaction.user.id, True, interaction)

    @discord.ui.button(label="Vote No", style=discord.ButtonStyle.red)
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self.lock:
            await self.handle_vote(interaction.user.id, False, interaction)

    async def handle_vote(self, user_id, vote, interaction):
        if user_id in self.votes:
            await interaction.response.send_message("You have already voted!", ephemeral=True)
            return

        # Record the user's vote
        self.votes[user_id] = vote
        await interaction.response.send_message(f"You voted {'Yes' if vote else 'No'}!", ephemeral=True)

        # Update vote status message
        await self.update_vote_status(interaction)

        if len(self.votes) == len(self.players):
            await self.evaluate_votes()

        # Disable the button after use
        await interaction.message.edit(view=self)

    async def update_vote_status(self, interaction):
        vote_status = ""
        for player_id in self.players:
            player = await bot.fetch_user(player_id)
            if player_id in self.votes:
                vote_status += f"{player.display_name}: {
                    '✅ Voted' if self.votes[player_id] else '✅ Voted'}\n"
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
        yes_votes = sum(1 for vote in self.votes.values() if vote)
        no_votes = len(self.votes) - yes_votes

        # Show final voting breakdown
        final_vote_status = ""
        for player_id, vote in self.votes.items():
            player = await bot.fetch_user(player_id)
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
        await self.vote_message.edit(embed=embed)

        channel = await bot.fetch_channel(self.session['channel_id'])

        if yes_votes > no_votes:
            # Government is elected
            self.session['state'] = 'legislative_session'
            self.session['election_tracker'] = 0

            # Notify about the successful election
            president = self.session['president']
            message = f"The government has been elected. Proceeding to the legislative session. <@{
                president}>, please discard a policy in your DM."
            await channel.send(message)

            # Proceed to the legislative session
            await legislative_session(self.ctx, self.session, channel)
        else:
            # Election fails, advance the election tracker
            await self.handle_failed_election()

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

        if self.session['election_tracker'] >= 3:
            # Chaos occurs: enact the top policy
            await self.enact_top_policy_due_to_chaos(channel)
        else:
            # Start the next election round
            await self.start_next_election()

    async def enact_top_policy_due_to_chaos(self, channel):
        # Enact the top policy automatically due to chaos
        if len(POLICIES) == 0:
            # If the policy deck is empty, shuffle the discard pile back into the policy deck
            POLICIES.extend(self.session.get('discard_pile', []))
            self.session['discard_pile'] = []
            random.shuffle(POLICIES)

        top_policy = POLICIES.pop(0)
        self.session['enacted_policies'].append(top_policy)
        self.session['election_tracker'] = 0  # Reset the Election Tracker

        # Announce the policy that has been enacted
        await channel.send(f"Three elections have failed. The country is in chaos, and the top policy has been enacted: **{top_policy}**.")

        # Handle executive actions if necessary
        if top_policy == "Fascist":
            # Pick a random executive action based on the number of enacted Fascist policies
            powers = ['investigate_loyalty',
                      'call_special_election', 'policy_peek', 'execution']
            fasc_count = sum(
                1 for p in self.session['enacted_policies'] if p == 'Fascist')
            if 1 <= fasc_count < 6:
                self.session['executive_action'] = powers[fasc_count - 2]
            await handle_executive_action(self.ctx, self.session, channel)
        else:
            await self.start_next_election()

    async def start_next_election(self):
        # Rotate the President and start the next election round
        await start_next_round(self.ctx, self.session, await bot.fetch_channel(self.session['channel_id']))

async def veto_power(ctx, session, channel):
    president = await bot.fetch_user(session['president'])
    chancellor = await bot.fetch_user(session['chancellor'])

    await channel.send(f"{president.mention} and {chancellor.mention}, you may now veto a policy if you both agree.")

    # Present the veto option to the Chancellor
    view = VetoView(president, chancellor, session, channel)
    await chancellor.send("Do you wish to veto the remaining policies?", view=view)


class VetoView(View):
    def __init__(self, president, chancellor, session, channel):
        super().__init__()
        self.president = president
        self.chancellor = chancellor
        self.session = session
        self.channel = channel

    @discord.ui.button(label="Veto", style=discord.ButtonStyle.red)
    async def veto(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.chancellor.id:
            await interaction.response.send_message("Only the Chancellor can initiate a veto.", ephemeral=True)
            return

        await interaction.response.send_message("You have chosen to veto the policies. Awaiting the President's approval.")

        # Wait for the President's decision
        view = ConfirmVetoView(self.president, self.session, self.channel)
        await self.president.send("The Chancellor has chosen to veto the policies. Do you agree to the veto?", view=view)


class PlayerSelect(discord.ui.Select):
    def __init__(self,players, session, placeholder):
        self.session = session
        
        options = [discord.SelectOption(
            label=user.display_name, value=user.id) for user in players]
        super().__init__(placeholder=placeholder,
                         min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        self.channel = await bot.fetch_channel(self.session['channel_id'])
        if session.get('executive_action') == 'investigate_loyalty':
            player_id = int(self.values[0])
            player = await bot.fetch_user(player_id)

            # Show the President the Party Membership of the selected player
            party_membership = self.session['roles'][player_id]
            president = await bot.fetch_user(self.session['president'])
            await president.send(f"The party membership of {player.name} is **{party_membership}**.")

            # Notify the channel that the investigation has been completed
            await self.channel.send(f"{president.mention} has completed an investigation of {player.mention}.")

            await start_next_round(interaction, self.session, self.channel)

        elif session.get('executive_action') == 'call_special_election':
            selected_player_id = int(self.values[0])
            selected_player = await bot.fetch_user(selected_player_id)

            # Assign the selected player as the next Presidential Candidate
            self.session['president'] = selected_player_id
            await self.channel.send(f"{selected_player.mention} has been selected as the next Presidential Candidate.")

            # Move to the Chancellor nomination phase
            await start_election_round(interaction, self.session, self.channel)
        elif session.get('executive_action') == 'execution':
            executed_player_id = int(self.values[0])
            executed_player = await bot.fetch_user(executed_player_id)

            # Notify the channel of the execution
            await self.channel.send(f"{executed_player.mention} has been executed.")

            # Check if the executed player is Hitler
            if self.session['roles'][executed_player_id] == "Hitler":
                await self.channel.send("The executed player was Hitler! The Liberals win!")
                self.session['state'] = 'game_end'
            else:
                await self.channel.send("The executed player was not Hitler. The game continues.")

            # Remove the executed player from the game
            self.session['players'].remove(executed_player_id)
            if executed_player_id in self.session.get('last_government', {}).values():
                del self.session['last_government']

            save_game_state()

            # If the game is not over, move to the next round
            if self.session['state'] != 'game_end':
                await start_next_round(interaction, self.session, self.channel)


class InvestigateLoyaltyView(View):
    def __init__(self,players, session, channel):
        super().__init__()
        self.session = session
        self.channel = channel
        self.add_item(PlayerSelect(players,session, placeholder="Select a player to investigate..."))


class SpecialElectionView(View):
    def __init__(self,players, session, channel):
        super().__init__()
        self.session = session
        self.channel = channel
        self.add_item(PlayerSelect(players,
            session, placeholder="Select a player to become the next Presidential Candidate..."))


class ExecutionView(View):
    def __init__(self,players, session, channel):
        super().__init__()
        self.session = session
        self.channel = channel
        self.add_item(PlayerSelect(players,
            session, placeholder="Select a player to execute..."))


async def handle_executive_action(ctx, session, channel):
    president = await bot.fetch_user(session['president'])
    players = []
    guild = bot.get_guild(session['guild_id'])
    for member in guild.members:  # Use the fetched guild object
        if member.id in session['players']:
            players.append(member)
    if session.get('executive_action') == 'investigate_loyalty':
        await channel.send(f"{president.mention}, you have the power to investigate the loyalty of one player.")
        # Present options to the President
        view = InvestigateLoyaltyView(players, session, channel)
        await president.send("Select a player to investigate their loyalty:", view=view)

    elif session.get('executive_action') == 'call_special_election':
        await channel.send(f"{president.mention}, you have the power to call a special election.")
        # Present options to the President
        view = SpecialElectionView(players, session, channel)
        await president.send("Select a player to become the next Presidential Candidate:", view=view)

    elif session.get('executive_action') == 'policy_peek':
        await channel.send(f"{president.mention}, you have the power to peek at the top three policies.")
        # Show the top three policies to the President
        top_policies = POLICIES[:3]
        await president.send(f"The top three policies in the deck are: {', '.join(top_policies)}.")
        await channel.send(f"{president.mention} has peeked at the top three policies.")
        await start_next_round(ctx, session, channel)

    elif session.get('executive_action') == 'execution':
        await channel.send(f"{president.mention}, you have the power to execute one player.")
        # Present options to the President
        view = ExecutionView(players, session, channel)
        await president.send("Select a player to execute:", view=view)

    else:
        await channel.send(f"No executive action to perform. Proceeding to the next round.")
        await start_next_round(ctx, session, channel)

async def handle_failed_election(ctx, session, channel):
    session['election_tracker'] += 1
    await channel.send(f"The election has failed. The Election Tracker is now at {session['election_tracker']}.")

    if session['election_tracker'] >= 3:
        await enact_top_policy_due_to_chaos(ctx, session, channel)
    else:
        await start_next_round(ctx, session, channel)

    save_game_state()


async def enact_top_policy_due_to_chaos(ctx, session, channel):
    if len(POLICIES) == 0:
        # If the policy deck is empty, shuffle the discard pile back into the policy deck
        POLICIES.extend(session.get('discard_pile', []))
        session['discard_pile'] = []
        random.shuffle(POLICIES)

    # Enact the top policy automatically
    top_policy = POLICIES.pop(0)
    session['enacted_policies'].append(top_policy)
    session['election_tracker'] = 0  # Reset the Election Tracker

    # Announce the policy that has been enacted
    await channel.send(f"Three elections have failed. The country is in chaos, and the top policy has been enacted: **{top_policy}**.")

    # Check if there is any special action related to this policy (e.g., Executive Power)
    if top_policy == "Fascist":
        await handle_executive_action(ctx, session, channel)
    else:
        await start_next_round(ctx, session, channel)

    save_game_state()

class ConfirmVetoView(View):
    def __init__(self, president, session, channel):
        super().__init__()
        self.president = president
        self.session = session
        self.channel = channel

    @discord.ui.button(label="Agree to Veto", style=discord.ButtonStyle.green)
    async def agree(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.president.id:
            await interaction.response.send_message("Only the President can agree to the veto.", ephemeral=True)
            return

        await interaction.response.send_message("You have agreed to the veto. The policies are discarded, and the Election Tracker advances.")

        # Discard the policies and advance the Election Tracker
        self.session['discard_pile'].extend([self.session['policies_drawn']])
        self.session['election_tracker'] += 1

        await self.channel.send(f"The veto has been agreed upon. The Election Tracker is now at {self.session['election_tracker']}.")

        if self.session['election_tracker'] >= 3:
            await enact_top_policy_due_to_chaos(interaction, self.session, self.channel)
        else:
            await start_next_round(interaction, self.session, self.channel)

        save_game_state()

    @discord.ui.button(label="Reject Veto", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.president.id:
            await interaction.response.send_message("Only the President can reject the veto.", ephemeral=True)
            return

        await interaction.response.send_message("You have rejected the veto. The Chancellor must enact a policy.")

        # Continue with the policy enactment process
        chancellor = await bot.fetch_user(self.session['chancellor'])
        policies_remaining = self.session['policies_drawn']

        # Create and send the dropdown for policy enactment
        select = EnactPolicySelect(policies_remaining)
        view = View()
        view.add_item(select)

        await chancellor.send(f"{chancellor.mention}, please select a policy to enact from the dropdown below:", view=view)

class PolicySelect(Select):
    def __init__(self, policies):
        options = [discord.SelectOption(
            label=policy, value=f"{policy}-{i}") for i, policy in enumerate(policies)]
        super().__init__(placeholder="Select a policy to discard...",
                         min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
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
        #POLICIES.append(policy)
        try:
            session['discard_pile'].extend([policy])
        except KeyError:
            session['discard_pile'] = [policy]
        session['policies_drawn'].remove(policy)
        POLICIES.remove(policy)
        await interaction.response.send_message(f"You have discarded the **{policy}** policy. The remaining policies will be sent to the chancellor.")
        save_game_state()

        # Disable the dropdown after selection
        self.disabled = True
        await interaction.message.edit(view=self.view)

        # Move to the Chancellor's policy enactment phase
        await enact_policy(interaction, session, session['channel_id'])


async def legislative_session(ctx, session, channel):
    president = await bot.fetch_user(session['president'])
    chancellor = await bot.fetch_user(session['chancellor'])

    # President draws top 3 policies:
    if len(POLICIES) < 5:
        POLICIES.extend(session.get('discard_pile', []))
        session['discard_pile'] = []
        random.shuffle(POLICIES)
    policies_drawn = POLICIES[:3]
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
    def __init__(self, ctx, policies):
        self.ctx = ctx
        options = [discord.SelectOption(
            label=policy, value=f"{policy}-{i}") for i, policy in enumerate(policies)]
        super().__init__(placeholder="Select a policy to enact...",
                         min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        global enacted_policy
        guild_id = channel.guild.id
        session = game_sessions.get(guild_id)
        if len([p for p in session['enacted_policies'] if p == 'Fascist']) >= 5:
            # Give the Chancellor the option to veto
            president = await bot.fetch_user(session['president'])
            chancellor = await bot.fetch_user(session['chancellor'])
            view = VetoView(president, chancellor, session, channel)
            await interaction.response.send_message(f"{interaction.user.mention}, you may veto this agenda if the President agrees.", view=view, ephemeral=True)

        else:
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
            POLICIES.remove(enacted_policy)
            await interaction.response.send_message(
                f"You have enacted the **{enacted_policy}** policy!  Head over to {channel.mention}")
            if enacted_policy == 'Fascist':
                color = discord.Color.red()
            else:
                color = discord.Color.blue()
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
            self.disabled = True
            await interaction.message.edit(view=self.view)
            await self.handle_policy_enactment()
    async def handle_policy_enactment(self):
        try:
            session['enacted_policies'].append(enacted_policy)
        except KeyError:
            session['enacted_policies'] = [enacted_policy]
        policies_remaining = session['policies_drawn']
        if enacted_policy:
            policies_remaining.remove(enacted_policy)

        

        # Check for game end conditions
        fasc_count = sum(
            1 for p in session['enacted_policies'] if p == 'Fascist')
        lib_count = sum(
            1 for p in session['enacted_policies'] if p == 'Liberal')
        fasc_tracker = f"GameAssets/Fascist Tracker {fasc_count}.png"
        lib_tracker = f"GameAssets/Liberal Tracker {
            session['election_tracker']}-{lib_count}.png"
        
        if os.path.isfile(fasc_tracker):
            file = discord.File(fasc_tracker, filename="fasctracker.png")
            await channel.send(file=file)
        if os.path.isfile(lib_tracker):
            file = discord.File(lib_tracker, filename="libtracker.png")
            await channel.send(file=file)
            
        powers = ['investigate_loyalty',
                  'call_special_election', 'policy_peek', 'execution']
          # check number of policies employed that are fascist:
        session['last_government'] = {
            'president': session['president'], 'chancellor': session['chancellor']}
        if enacted_policy == 'Fascist' and fasc_count > 1 and fasc_count < 6:
            session['executive_action'] = powers[fasc_count-2]
            await handle_executive_action(self.ctx, session, channel)
            if fasc_count >= 3:
                if session['roles'][session['chancellor']] == 'Hitler':
                    await channel.send("The Chancellor was Hitler! The Fascists win!")
                    session['state'] = 'game_end'
                    await end_game(None, "Fascist")
                else:
                    await channel.send("The Chancellor is not Hitler. The game continues.")
                    session['state'] = 'new_round'
                    save_game_state()
                    await start_next_round(self.ctx, session, channel)
        elif enacted_policy == 'Liberal' and lib_count >= 5:
            await channel.send("The Liberals have enacted five policies! The Liberals win!")
            session['state'] = 'game_end'
            await end_game(None, "Liberal")
        else:
            #store previous chancellor:
            session['state'] = 'new_round'
            save_game_state()
            await asyncio.sleep(10)
            await start_next_round(self.ctx, session, channel)


async def enact_policy(ctx, session, channel):
    global enacted_policy
    chancellor = await bot.fetch_user(session['chancellor'])

    # Chancellor receives 2 remaining policies
    policies_remaining = session['policies_drawn']

    # Create and send the dropdown
    select = EnactPolicySelect(ctx, policies_remaining)
    view = View()
    view.add_item(select)

    await chancellor.send(f"{chancellor.mention}, please select a policy to enact from the dropdown below:", view=view)

    session['state'] = 'policy_enactment'
    save_game_state()


async def start_next_round(ctx, session, channel):
    # Rotate the President to the next player
    players = session['players']
    current_president_index = players.index(session['president'])
    next_president_index = (current_president_index + 1) % len(players)
    session['president'] = players[next_president_index]

    # Clear the previous chancellor and chancellor candidate
    session['chancellor'] = None
    session['chancellor_candidate'] = None

    # Move back to the election phase
    await start_election_round(ctx, session, channel)


@bot.hybrid_command(name="end_game", description="End the current Secret Hitler game session")
@commands.has_permissions(administrator=True)
async def end_game(ctx: commands.Context, winner:str = None):
    global channel
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

        del game_sessions[guild_id]
        save_game_state()

        embed = discord.Embed(
            title="Game Ended",
            description="The current game session has been terminated.",
            color=discord.Color.red()
        )
        # delete channel:
        await ctx.send(embed=embed)
   
            
    corresponding_role = ""
    for player in session['players']:
        user = await bot.fetch_user(player)
        corresponding_role += f"{user.display_name}: {session['roles'][player]}\n"
    if winner == "Fascist":
        desc = "**Fascists** Win!"
        color = discord.Color.orange()
    elif winner == "Liberal":
        desc = "**Liberals** Win!"
        color = discord.Color.blue()
    else:
        desc = "Game Terminated"
        color = discord.Color.red()
    final_embed = discord.Embed(
        title="Game Ended",
        description=desc,
        color=color
    )
    final_embed.add_field(name="Roles", value=corresponding_role)
    initchannel = session['init_channel']
    initchannel = await bot.fetch_channel(initchannel)
    await initchannel.send(embed=final_embed)

    await asyncio.sleep(5)
    await channel.delete()

# Load the bot with your token

# Load the .env file
dotenv.load_dotenv()
bot.run(os.getenv('TOKEN'))
