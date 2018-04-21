import asyncio
import discord
import os
import os.path
from discord.ext import commands



class VoiceEntry:
    def __init__(self, message, player, song = None):
        self.requester = message.author
        self.channel = message.channel
        self.player = player
        self.song = song

    def __str__(self):
        fmt = '{0.title}, by {0.artist}. Requested by {1.display_name}' # string formats. Yay
        return fmt.format(self.song, self.requester)

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
            await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current))
            self.current.player.start()
            await self.play_next_song.wait()

# actuall bot commands 'n stuff'
class Music_Bot:
    """Voice related commands.
    Works in multiple servers at once.
    """
    def __init__(self, bot, music_path, music_database, Beets):
        self.bot = bot
        self.voice_states = {}
        self.music_path = music_path
        self.music_database = music_database
        self.BEETS = Beets

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

    @commands.command(pass_context=True)
    async def search(self, ctx, query: str):
        """Searches music database for items that match the string given
        May search for titles, album names, artists, genres, ect
        To search specifically for albums, use !search "Album:Albumname" with quotes
        To search for genres, !search "genre:genrename"
        For a full list of items to search by, find Merl/Xellophane, and bug him to finish this poor soul with complete docs."""
        query = query
        items = self.BEETS.query_items(query)
        fmt = []
        count = 0
        await self.bot.say("Results for " + query)
        print("User performed search")
        for item in items:
            string = "{} by '{}'"

            count += len(string.format(item.title, item.artist))
            fmt.append(string.format(item.title, item.artist))
            print(string.format(item.title, item.artist))
            if count >= 1500:
                await self.bot.say(fmt)
                fmt = []
                print(count)
                count = 0

        await self.bot.say(fmt)

    @commands.command(pass_context=True)
    async def albums(self, ctx):
        """Lists all the available albums in the database"""
        items = self.BEETS.query_albums()
        fmt = []
        count = 0
        print("User Listing ALL albums")
        for item in items:
            string = "{} by '{}'"
            # limit how many items can be strung together in a message
            count += len(string.format(item.album, item.albumartist))
            fmt.append(string.format(item.album, item.albumartist))
            if count >= 1500:
                await self.bot.say(fmt)
                fmt = []
                print(count)
                count = 0

        await self.bot.say(fmt)

    @commands.command(pass_context=True)
    async def all_songs(self, ctx):
        """Lists all the available songs in the database"""
        items = self.BEETS.query_items()
        fmt = []
        count = 0
        print("User Listing ALL songs")
        for item in items:
            string = "{} by '{}'"
            # limit how many items can be strung together in a message
            fmt.append(string.format(item.title, item.artist))
            count += len(string.format(item.title, item.artist))
            if count >= 1500:
                await self.bot.say(fmt)
                fmt = []
                print(count)
                count = 0

        await self.bot.say(fmt)

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
    async def leave(self, ctx):
        """forces the bot to leave the voice channel it is currently in."""

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            await self.bot.say("I am not in a voice channel")
        else:
            await state.voice.disconnect()

    @commands.command(pass_context=True)
    async def banish(self, ctx):
        """Banish the bot from all servers it's a part of and logs it out"""
        await self.bot.logout()

    @commands.command(pass_context=True)
    async def play(self, ctx, volume, *, song : str):
        """Plays a song.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """
        state = self.get_voice_state(ctx.message.server)
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }
        songs = []
        song = song
        items = self.BEETS.query_items(song)

        if items[0]:
            self.song = items[0]

        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        try:
            player = state.voice.create_ffmpeg_player(self.song.path.decode(), after=state.toggle_next)
            player.volume = int(volume) / 100
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            entry = VoiceEntry(ctx.message, player, self.song)
            fmt = 'Playing ```py\n{}: {}\n```'
            await self.bot.say('Enqueued ' + self.song.title)
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
                song = self.song
                await self.bot.say('Now playing {} @ {:.0%} volume [skips: {}/3] '.format(self.song.title, skip_count))
            else:
                await self.bot.say('Not playing anything.')
        else:
            skip_count = len(state.skip_votes)
            if hasattr(state.current.player, 'url'):
                await self.bot.say('Now playing {} [skips: {}/3]'.format(state.current.player.url, skip_count))
