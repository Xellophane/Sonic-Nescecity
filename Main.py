# imports
import asyncio
import discord
import os
import os.path
import glob
from discord.ext import commands

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

music_directory = '/home/kogatlas/Music/'
class Library:
    """Object to hold all the albums"""
    def __init__(self):
        self.albums = os.listdir(music_directory)

class Album:
    def __init__(self, name):
        """Not too sure what I'm going to do with this class. If I make use of it,
        it will be to allow the entire album to be loaded, queued, and maybe shuffled"""

        self.name = name
        self.music_directory = os.path.join(music_directory, name, "MP3/") # directory where the music is held. Note that python should convert to windows and unix
        # This should be the meat and potatoes, as it should grab everything in the albums FLAC/MP3 directory and put it into a list.
        self.songs = glob.glob(self.music_directory + "*.mp3")



class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player

    def __str__(self):
        fmt = '{0.player} requested by {1.display_name}' # Something to do with strings? iono
        # duration = self.player.duration
        # if duration:
            # fmt = fmt + ' [length: {0[0]}m {0[1]}s]'.format(divmod(duration, 60))
        return fmt.format(self.player, self.requester)

# this class allows the bot to exist in multiple servers.
class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        self.songs = asyncio.Queue()
        self.skip_votes = set() # a set of user_ids that voted
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    # getters and setters stuff
    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.player.stop()

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        while True:
            self.play_next_song.clear()
            self.current = await self.songs.get()
            # print(self.current)
            # print(str(self.current))
            # print(dir(self.current.player))
            # print(vars(self.current.player))
            if hasattr(self.current.player, 'url'):
                await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current.player.url))
            else:
                await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current.player.getName()))
            self.current.player.start()
            await self.play_next_song.wait()

# actuall bot commands 'n stuff'
class Music:
    """Voice related commands.
    Works in multiple servers at once.
    """
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}
        self.album = None
        self.library = Library()

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        voice = await self.bot.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    # @commands.command(pass_context=True)
    # async def commands(self, ctx):
        # pass

    @commands.command(pass_context=True)
    async def join(self, ctx, *, channel : discord.Channel):
        """Joins a voice channel."""
        try:
            await self.create_voice_client(channel)
        except discord.ClientException:
            await self.bot.say('Already in a voice channel...')
        except discord.InvalidArgument:
            await self.bot.say('This is not a voice channel...')
        else:
            await self.bot.say('Ready to play audio in ' + channel.name)

    @commands.command(pass_context=True)
    async def summon(self, ctx):
        """Summons the bot to join your voice channel."""
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say('You are not in a voice channel.')
            return False

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            state.voice = await self.bot.join_voice_channel(summoned_channel)
        else:
            await state.voice.move_to(summoned_channel)

        return True

    @commands.command(pass_context=True)
    async def banish(self, ctx):
        """Banish the bot from all servers it's a part of and logs it out"""
        await bot.logout()

    @commands.command(pass_context=True)
    async def list_cwd(self, ctx):
        """Returns all the files matching search entry"""
        cwd = glob.glob('*.flac')
        await self.bot.send_message(ctx.message.channel, glob.glob('*.flac'))

    @commands.command(pass_context=True)
    async def chalbum(self, ctx, albumnumber):
        """ Changes to selected album by name or index
        """
        if albumnumber.isdigit():
            number = int(albumnumber)
        else:
            for idx, item in enumerate(self.library.albums):
                itemTitle = item[item.rfind('/') + 1:]
                if albumnumber.lower() in itemTitle.lower():
                    number = idx
        """Changes the album to inputed album, does not do if album doesn't exist"""
        self.album = Album(self.library.albums[number])
        await self.bot.send_message(ctx.message.channel, os.listdir(self.album.music_directory))
        # TODO: add in meta data for song titles.

    @commands.command(pass_context=True)
    async def list_albums(self, ctx):
        """ Lists available albums.
        Same as !albums.
        """
        await self.bot.send_message(ctx.message.channel, self.library.albums)

    @commands.command(pass_context=True)
    async def albums(self, ctx):
        """ Lists available albums.
        Same as !list_albums.
        """
        await self.bot.send_message(ctx.message.channel, self.library.albums)

    @commands.command(pass_context=True)
    async def play(self, ctx, *, song : str):
        """Plays a song.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        """
        state = self.get_voice_state(ctx.message.server)
        self.song = '';
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }

        if song.isdigit():
            self.song = int(song)
        else:
            for idx, item in enumerate(self.album.songs):
                itemTitle = item[item.rfind('/') + 1:]
                if song.lower() in itemTitle.lower():
                    self.song = idx

        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        if type(self.song) == int:
            try:
                player = state.voice.create_ffmpeg_player(self.album.songs[self.song], after=state.toggle_next)
            except Exception as e:
                fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
                await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
            else:
                entry = VoiceEntry(ctx.message, player)
                prettySong = self.album.songs[self.song][item.rfind('/') + 1:]
                await self.bot.say('Enqueued ' + prettySong[:prettySong.rfind('.')])
                entry.player.setName(prettySong[:prettySong.rfind('.')])
                print (dir(entry.player))
                print (vars(entry.player))
                await state.songs.put(entry)
        else:
            await self.bot.send_message(ctx.message.channel, "No song matching your request was found.")

    @commands.command(pass_context=True, no_pm=True)
    async def search(self, ctx, *, song : str):
        """Searches YouTube for a song matching your request.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """
        state = self.get_voice_state(ctx.message.server)
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }

        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        try:
            player = await state.voice.create_ytdl_player(song, ytdl_options=opts, after=state.toggle_next)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            player.volume = 0.6
            entry = VoiceEntry(ctx.message, player)
            await self.bot.say('Enqueued ' + player.url)
            await state.songs.put(entry)

    @commands.command(pass_context=True)
    async def volume(self, ctx, value : int):
        """Sets the volume of the currently playing song."""

        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.volume = value / 100
            await self.bot.say('Set the volume to {:.0%}'.format(player.volume))

    @commands.command(pass_context=True)
    async def pause(self, ctx):
        """Pauses the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.pause()

    @commands.command(pass_context=True)
    async def resume(self, ctx):
        """Resumes the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.resume()

    @commands.command(pass_context=True)
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.
        """
        server = ctx.message.server
        state = self.get_voice_state(server)

        if state.is_playing():
            player = state.player
            player.stop()

        try:
            state.audio_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except:
            pass

    @commands.command(pass_context=True)
    async def skip(self, ctx):
        """Vote to skip a song. The song requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        voter = ctx.message.author
        if voter == state.current.requester:
            await self.bot.say('Requester requested skipping song...')
            state.skip()
        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)
            if total_votes >= 3:
                await self.bot.say('Skip vote passed, skipping song...')
                state.skip()
            else:
                await self.bot.say('Skip vote added, currently at [{}/3]'.format(total_votes))
        else:
            await self.bot.say('You have already voted to skip this song.')

    @commands.command(pass_context=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        print(state.current.player)
        if not hasattr(state.current.player, 'url'):
            if self.song != None:
                skip_count = len(state.skip_votes)
                song = self.album.songs[self.song]
                prettySong = song[song.rfind('/') + 1:]
                await self.bot.say('Now playing {} [skips: {}/3]'.format(prettySong[:prettySong.rfind('.')], skip_count))
            else:
                await self.bot.say('Not playing anything.')
        else:
            skip_count = len(state.skip_votes)
            if hasattr(state.current.player, 'url'):
                await self.bot.say('Now playing {} [skips: {}/3]'.format(state.current.player.url, skip_count))

    @commands.command(pass_context=True)
    async def list_songs(self, ctx):
        """ Lists available songs for current album.
        Same as !songs.
        """
        prettyAlbum = []
        for item in self.album.songs:
            prettyAlbum.append(item[item.rfind('/') + 1:])
        await self.bot.send_message(ctx.message.channel, prettyAlbum)

    @commands.command(pass_context=True)
    async def songs(self, ctx):
        """ Lists available songs for current album.
        Same as !list_songs.
        """
        prettyAlbum = []
        for item in self.album.songs:
            prettyAlbum.append(item[item.rfind('/') + 1:])
        await self.bot.send_message(ctx.message.channel, prettyAlbum)

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'), description='A playlist example for discord.py')
bot.add_cog(Music(bot))

@bot.event
async def on_ready():
    print('Logged in as: \n{0} (ID: {0.id})'.format(bot.user))

pfile = open("Password.txt", "r")
password = pfile.readline()
pfile.close()
password = password.rstrip()
password = str(password)

bot.run(password)
