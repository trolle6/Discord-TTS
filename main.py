import os
import discord
from discord.ext import commands
import boto3
import asyncio

# Discord bot settings
TOKEN = 'Discord-Bot-Token'
GUILD = 'Server-Name'

# AWS settings
AWS_ACCESS_KEY_ID = 'AWS-Access-Key'
AWS_SECRET_ACCESS_KEY = 'AWS-Secret-Key'
AWS_REGION = 'Region-Code'

# Boto3 Polly client
polly = boto3.client('polly', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)

# Discord bot settings
intents = discord.Intents().all()
intents.members = True
bot = commands.Bot(command_prefix='', intents=intents)

# Message queue settings
message_queue = asyncio.Queue()
is_speaking = False  # flag to check if bot is currently speaking

# Whitelist settings
whitelist = ['User1#0001', 'User2#0002', 'User3#0003']
whitelist_role_name = 'Role-Name' # the name of the role that can add to the whitelist

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
        await asyncio.sleep(0.5)  # add a short delay to ensure the file is created before playing
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
@commands.has_role(whitelist_role_name)
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
    if message.channel.name == 'Channel-Name':
        if not message.author.bot:
            if message.author.name + '#' + message.author.discriminator in whitelist:
                if message.content.strip():
                    if not is_speaking:  # check if bot is currently speaking
                        await message_queue.put(message.content)
                        if not bot.voice_clients:
                            vc = await message.author.voice.channel.connect()
                            asyncio.ensure_future(speak_message(vc))
                    else:
                        await message.channel.send('Sorry, I am currently speaking. Please wait for me to finish before sending another message.')
            else:
                await message.channel.send('Sorry, you do not have access to use this bot.')
    await bot.process_commands(message)

# Asynchronous tasks
async def check_voice_channels():
    while True:
        for vc in bot.voice_clients:
            if not vc.is_playing() and not vc.is_paused() and not vc.is_connected():
                await vc.disconnect()
        await asyncio.sleep(4)

async def check_empty_vc():
