from discord import Embed, Color
from discord.ext.commands import Bot
from discord.ext.commands.core import Command
from guild_music_player import GuildMusicPlayer
import youtube_dl
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import dotenv

dotenv.load_dotenv()


class BoganBot(Bot):
    guild_music_players = {}
    youtube_info_downloader = youtube_dl.YoutubeDL({
        'format': 'bestaudio/best',
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    })
    spotify_auth_manager = SpotifyClientCredentials()
    spotify = spotipy.Spotify(auth_manager=spotify_auth_manager)

    SPOTIFY_TRACK_URL = "https://open.spotify.com/track/"

    def __init__(self, command_prefix="!"):
        super().__init__(command_prefix)
        self.add_command(Command(self.join, name="join",
                                 aliases=["j"], brief="Tell the bot to join your current voice channel.", pass_context=True))
        self.add_command(Command(self.play, name="play",
                         aliases=["p"], brief="Play the requested song.", pass_context=True))
        self.add_command(Command(self.skip, name="skip",
                         aliases=["s"], brief="Skip the currently playing track.", pass_context=True))
        self.add_command(Command(self.clear, name="clear",
                         aliases=["c"], brief="Clear all songs from the queue.", pass_context=True))
        self.add_command(Command(self.list, name="list",
                         aliases=["l"], brief="List the next songs in the queue.", pass_context=True))
        self.add_command(Command(self.commands, name="commands",
                         brief="Show the commands list.", pass_context=True))

    async def commands(self, context):
        commands_message = "The following commands are available:"
        for command_name in self.all_commands:
            command = self.get_command(command_name)
            if command_name in command.aliases:
                continue
            command_aliases = [self.command_prefix +
                               alias for alias in command.aliases]
            commands_message += "\n{0}{1} (aliases: {2}) - {3}".format(
                self.command_prefix, command.name, command_aliases, command.brief)
        await self.embed_message(context, "Commands", commands_message)

    async def on_ready(self):
        for guild in self.guilds:
            await self.on_guild_join(guild)

    async def on_guild_join(self, guild):
        if guild not in self.guild_music_players.keys():
            guild_music_player = GuildMusicPlayer(guild, self)
            self.guild_music_players[guild] = guild_music_player
            self.loop.create_task(guild_music_player.play_next_song())
            print("[{0}] has connected to discord server [{1}] - creating a player for this server".format(
                self.user, guild.name))

    async def on_guild_remove(self, guild):
        self.guild_music_players.pop(guild)
        print("[{0}] has been removed from the discord server [{1}] - creating a player for this server".format(
            self.user, guild.name))

    async def join(self, context):
        message_author = context.message.author
        voice_info = message_author.voice
        guild = context.message.guild
        connected = False
        if not voice_info:
            await context.send("{0} you need to be in a voice channel for the bot to join.".format(message_author.mention))
        else:
            voice_channel = voice_info.channel
            if not guild.voice_client or \
                    (guild.voice_client and not guild.voice_client.is_connected()):
                await voice_channel.connect()
            connected = True
        return connected

    async def play(self, context, *song_search):
        song_name = " ".join(song_search)
        caller = context.message.author
        guild = context.message.guild
        if song_name.startswith(self.SPOTIFY_TRACK_URL):
            print("[{0}] searched for {1} which appears to be a spotify track on server [{2}]".format(
                caller, song_name, guild.name))
            spotify_track = self.spotify.track(song_name)
            artist = spotify_track['artists'][0]['name']
            track_name = spotify_track['name']
            song_name = "{0} {1}".format(artist, track_name)
            print("Found actual song name {0}".format(song_name))
        if await self.join(context):
            argument_string = context.message.content.replace(
                context.prefix+context.command.name+" ", "")
            if song_name is not None and len(song_name.strip()) > 0:
                song_metadata = await self.get_song_metadata(song_name)
                songname = song_metadata['title']
                guild_player = self.guild_music_players[guild]
                await guild_player.queue_song(context, song_metadata)
                if guild.voice_client.is_playing():
                    await self.embed_message(context, "Song Queued",
                                             ("{0} queued {1}.\n\nThere are currently **{2}** tracks queued."
                                              .format(caller.mention, songname, guild_player.get_queue_size())))
                print("[{0}] queued up {1} with '{2}' for server [{3}]".format(
                    caller, songname, argument_string, guild.name))

    async def skip(self, context):
        caller = context.message.author
        voice_info_of_caller = caller.voice
        if voice_info_of_caller:
            voice_channel_of_caller = voice_info_of_caller.channel
            guild = context.message.guild
            guild_player = self.guild_music_players[guild]
            if voice_channel_of_caller in [client.channel for client in self.voice_clients]:
                if guild.voice_client.is_playing():
                    await self.embed_message(context, "Song Skipped",
                                             ("{0} skipped the current track..\n\nThere are currently **{1}** tracks queued."
                                              .format(caller.mention, guild_player.get_queue_size())))
                    print("[{0}] skipped the current track in server {1}".format(
                        caller, guild.name))
                    guild.voice_client.stop()

    async def clear(self, context):
        caller = context.message.author
        voice_info_of_caller = caller.voice
        if voice_info_of_caller:
            voice_channel_of_caller = voice_info_of_caller.channel
            guild = context.message.guild
            guild_player = self.guild_music_players[guild]
            if voice_channel_of_caller in [client.channel for client in self.voice_clients]:
                await self.embed_message(context, "Queue Cleared", ("{0} cleared the song queue..".format(caller.mention,)))
                print("[{0}] cleared the queue in server {1}".format(
                    caller, guild.name))
                await guild_player.clear_queue()

    async def list(self, context):
        caller = context.message.author
        guild = context.message.guild
        guild_player = self.guild_music_players[guild]
        songs_to_list = 5
        song_list = guild_player.list_song_queue(songs_to_list)
        playlist_message = ""
        i = 1
        for song in song_list:
            playlist_message += "{0}. {1}\n".format(i, song.title)
            i += 1
        await self.embed_message(context, "Current Playlist",
                                 (playlist_message+"\n\nThere are currently **{1}** tracks queued."
                                  .format(caller.mention, guild_player.get_queue_size())))

    async def embed_message(self, context, title, message):
        embed = Embed(title=title,
                      description=message,
                      color=Color.blue())
        await context.send(embed=embed)

    async def get_song_metadata(self, search):
        data = await self.loop.run_in_executor(None, lambda: self.youtube_info_downloader.extract_info(search, download=False))
        if 'entries' in data:
            data = data['entries'][0]
        return data
