# imports
import asyncio
import discord
import os
import os.path
import glob
import configparser
from discord.ext import commands

from Music import Music_Bot
from Beets import Beets

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')



# ConfigParser reads the files similaryly to a python dictionary.
# the config settings are:
# MUSIC_DIR
# API_KEY
# MUSIC_DATABASE

# assign the config parser, then open and read the file
config = configparser.ConfigParser()
config.read('config.ini')

# compact the config for more simple reading
baseconfig = config['Base Config']

# assign the music directory
MUSIC_DIRECTORY = baseconfig['MUSIC_DIR']

# grab the api key
API_KEY = baseconfig['API_KEY']

# Check if beets is enabled and assign the database if it is enabled.
BEETS_FUNCTIONALITY = bool(baseconfig['BEETS_FUNCTIONALITY'])
if BEETS_FUNCTIONALITY == True:
    MUSIC_DATABASE = baseconfig['MUSIC_DATABASE']
    BEETS = Beets(MUSIC_DATABASE)
else:
    MUSIC_DATABASE = None



bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'), description='A playlist example for discord.py')
bot.add_cog(Music_Bot(bot, MUSIC_DIRECTORY, MUSIC_DATABASE, BEETS))

@bot.event
async def on_ready():
    print('Logged in as: \n{0} (ID: {0.id})'.format(bot.user))


bot.run(API_KEY)
