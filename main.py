import os
import discord
from discord.ext import commands
import boto3
import asyncio
import configparser

# Read variables from configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# Discord bot settings
TOKEN = config['DISCORD']['TOKEN']
TEXT_CHANNEL_NAME = config['DISCORD']['TEXT_CHANNEL_NAME']
WHITELIST_ROLE_NAME = config['DISCORD']['WHITELIST_ROLE_NAME']

# Boto3 Polly client
AWS_ACCESS_KEY_ID = config['POLLY']['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = config['POLLY']['AWS_SECRET_ACCESS_KEY']
AWS_REGION = config['POLLY']['AWS_REGION']
polly = boto3.client('polly', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)

# Message queue settings
DELAY_SECONDS = float(config['MESSAGE_QUEUE_SETTINGS']['DELAY_SECONDS'])
message_queue = asyncio.Queue()
is_speaking = False

# Discord bot settings
intents = discord.Intents().all()
intents.members = True
bot = commands.Bot(command_prefix='', intents=intents)

# Discord bot commands
@bot.command(name='add_whitelist')
@commands.has_role(WHITELIST_ROLE_NAME)
async def add_whitelist(ctx, user):
    if user not in whitelist:
        whitelist.append(user)
        await ctx.send(f"{user} has been added to the whitelist.")
    else:
        await ctx.send(f"{user} is already in the whitelist.")

# Discord bot event handlers
async def speak_message(vc):
    global is_speaking
    while True:
        message = await message_queue.get()
        is_speaking = True
        response = polly.synthesize_speech(Text=message, OutputFormat='mp3', VoiceId='Matthew')
        file = open('speech.mp3', 'wb')
        file.write(response['AudioStream'].read())
        file.close()
        vc.play(discord.FFmpegPCMAudio('speech.mp3'))
        await asyncio.sleep(DELAY_SECONDS)
        while vc.is_playing():
            await asyncio.sleep(0.1)
        is_speaking = False

async def queue_messages(queue):
    while True:
        message = await queue.get()
        # do something with message
        print(message)

@bot.event
async def on_message(message):
    global is_speaking
    if message.channel.name == TEXT_CHANNEL_NAME:
        if not message.author.bot:
            if message.author.name + '#' + message.author.discriminator in whitelist:
                if message.content.strip():
                    if not is_speaking:
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
