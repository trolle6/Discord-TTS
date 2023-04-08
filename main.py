import os
import discord
from discord.ext import commands
import boto3
import asyncio
import configparser

# Read variables from configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# Boto3 Polly client
polly = boto3.client('polly', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)

# Discord bot settings
intents = discord.Intents().all()
intents.members = True
bot = commands.Bot(command_prefix='', intents=intents)

# Message queue settings
message_queue = asyncio.Queue()
is_speaking = False  # flag to check if bot is currently speaking
delay_seconds = float(config['MESSAGE_QUEUE_SETTINGS']['DELAY_SECONDS'])

# Discord bot event handlers
async def speak_message(vc):
    global is_speaking
    while True:
        message = await message_queue.get()
        is_speaking = True  # set flag to True when bot is speaking
        response = polly.synthesize_speech(Text=message, OutputFormat='mp3', VoiceId='Matthew')
        file = open('speech.mp3', 'wb')
        file.write(response['AudioStream'].read())
        file.close()
        vc.play(discord.FFmpegPCMAudio('speech.mp3'))
        await asyncio.sleep(delay_seconds)  # add a short delay to ensure the file is created before playing
        while vc.is_playing():  # wait until the message finishes playing
            await asyncio.sleep(0.1)
        is_speaking = False  # set flag to False when bot is done speaking

async def queue_messages(queue):
    while True:
        message = await queue.get()
        # do something with message
        print(message)

# Discord bot commands
@bot.command(name='add_whitelist')
@commands.has_role('whitelist_role_name') # change to actual role name
async def add_whitelist(ctx, user):
    if user not in whitelist:
        whitelist.append(user)
        await ctx.send(f"{user} has been added to the whitelist.")
    else:
        await ctx.send(f"{user} is already in the whitelist.")

# Discord bot event handlers
@bot.event
async def on_message(message):
    global is_speaking
    if message.channel.name == 'channel_name': # change to actual channel name
        if not message.author.bot:
            if message.author.name + '#' + message.author.discriminator in whitelist:
                if message.content.strip():
                    if not is_speaking:  # check if bot is currently speaking
                        await message_queue.put(message.content)
                        if message.author.voice and message.author.voice.channel:
                            vc = await message.author.voice.channel.connect()
                            bot.loop.create_task(speak_message(vc))
                        else:
                            await message.channel.send(f"{message.author.mention} Please join a voice channel first.")
        await bot.process_commands(message)

@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(f'{bot.user.name} has connected to Discord!')
        print(f'{guild.name}(id: {guild.id})')

bot.loop.create_task(queue_messages(message_queue))
bot.run(TOKEN)
