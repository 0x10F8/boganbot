import dotenv
import discord
import os
from discord import Embed, Color, client
from discord.ext.commands import Bot, Context
from guild_music_player import GuildMusicPlayer
import yt_dlp as youtube_dl
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import dotenv

dotenv.load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(command_prefix="!", intents=intents)

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
SPOTIFY_PLAYLIST_URL = "https://open.spotify.com/playlist/"


@bot.event
async def on_ready():
    for guild in bot.guilds:
        await on_guild_join(guild)

async def on_guild_join(guild):
    if guild not in guild_music_players.keys():
        guild_music_player = GuildMusicPlayer(guild, bot)
        guild_music_players[guild] = guild_music_player
        bot.loop.create_task(guild_music_player.play_next_song())
        print("[{0}] has connected to discord server [{1}] - creating a player for this server".format(
            bot.user, guild.name))

@bot.event
async def on_guild_remove(guild):
    guild_music_players.pop(guild)
    print("[{0}] has been removed from the discord server [{1}] - creating a player for this server".format(bot.user, guild.name))


@bot.command(name="join", aliases=["j"], brief="Tell the bot to join your current voice channel.")
async def join(context):
    message_author = context.message.author
    voice_info = message_author.voice
    guild = context.message.guild
    connected = False
    if not voice_info:
        await context.send("{0} you need to be in a voice channel for the bot to join.".format(message_author.mention))
    else:
        voice_channel = voice_info.channel
        if not guild.voice_client or (guild.voice_client and not guild.voice_client.is_connected()):
            await voice_channel.connect()
        connected = True
    return connected


@bot.command(name="move", aliases=["m"], brief="Move the bot to your channel.")
async def move(context):
    message_author = context.message.author
    voice_info = message_author.voice
    guild = context.message.guild
    connected = False
    if not voice_info:
        await context.send("{0} you need to be in a voice channel for the bot to join.".format(message_author.mention))
    else:
        voice_channel = voice_info.channel
        if not guild.voice_client or (guild.voice_client and not guild.voice_client.is_connected()):
            await voice_channel.connect()
        else:
            await guild.voice_client.move_to(voice_channel)
        connected = True
    return connected


async def play_playlist(context, song_name):
    caller = context.message.author
    guild = context.message.guild
    tracks = []
    playlist_name = ""
    if song_name.startswith(SPOTIFY_PLAYLIST_URL):
        print("[{0}] searched for {1} which appears to be a spotify playlist on server [{2}]".format(
            caller, song_name, guild.name))
        spotify_playlist = spotify.playlist(song_name)
        playlist_name = spotify_playlist['name']
        spotify_tracks = spotify_playlist['tracks']['items']
        for spotify_track in spotify_tracks:
            spotify_track = spotify_track['track']
            artist = spotify_track['artists'][0]['name']
            track_name = spotify_track['name']
            tracks.append("{0} {1}".format(artist, track_name))
    if await join(context):
        argument_string = context.message.content.replace(
            context.prefix+context.command.name+" ", "")
        if len(tracks) > 0:
            for track in tracks:
                song_metadata = await get_song_metadata(track)
                guild_player = guild_music_players[guild]
                await guild_player.queue_song(context, song_metadata)
            if guild.voice_client.is_playing():
                await embed_message(context, "Playlist Queued",
                                         ("{0} queued {1}.\n\nThere are currently **{2}** tracks queued."
                                             .format(caller.mention, playlist_name, guild_player.get_queue_size())))
            print("[{0}] queued up {1} with '{2}' for server [{3}]".format(
                caller, playlist_name, argument_string, guild.name))


@bot.command(name="play", aliases=["p"], brief="Play the requested song.")
async def play(context, *song_search):
    song_name = " ".join(song_search)
    context.send('test')
    caller = context.message.author
    guild = context.message.guild
    if song_name.startswith(SPOTIFY_PLAYLIST_URL):
        await play_playlist(context, song_name)
    else:
        if song_name.startswith(SPOTIFY_TRACK_URL):
            print("[{0}] searched for {1} which appears to be a spotify track on server [{2}]".format(
                caller, song_name, guild.name))
            spotify_track = spotify.track(song_name)
            artist = spotify_track['artists'][0]['name']
            track_name = spotify_track['name']
            song_name = "{0} {1}".format(artist, track_name)
            print("Found actual song name {0}".format(song_name))
        if await join(context):
            argument_string = context.message.content.replace(
                context.prefix+context.command.name+" ", "")
            if song_name is not None and len(song_name.strip()) > 0:
                song_metadata = await get_song_metadata(song_name)
                songname = song_metadata['title']
                guild_player = guild_music_players[guild]
                await guild_player.queue_song(context, song_metadata)
                if guild.voice_client.is_playing():
                    await embed_message(context, "Song Queued",
                                             ("{0} queued {1}.\n\nThere are currently **{2}** tracks queued."
                                                 .format(caller.mention, songname, guild_player.get_queue_size())))
                print("[{0}] queued up {1} with '{2}' for server [{3}]".format(
                    caller, songname, argument_string, guild.name))


@bot.command(name="skip", aliases=["s"], brief="Skip the currently playing track.")
async def skip(context):
    caller = context.message.author
    voice_info_of_caller = caller.voice
    if voice_info_of_caller:
        voice_channel_of_caller = voice_info_of_caller.channel
        guild = context.message.guild
        guild_player = guild_music_players[guild]
        if voice_channel_of_caller in [client.channel for client in bot.voice_clients]:
            if guild.voice_client.is_playing():
                await embed_message(context, "Song Skipped",
                                         ("{0} skipped the current track..\n\nThere are currently **{1}** tracks queued."
                                             .format(caller.mention, guild_player.get_queue_size())))
                print("[{0}] skipped the current track in server {1}".format(
                    caller, guild.name))
                guild.voice_client.stop()


@bot.command(name="clear", aliases=["c"], brief="Clear all songs from the queue.")
async def clear(context):
    caller = context.message.author
    voice_info_of_caller = caller.voice
    if voice_info_of_caller:
        voice_channel_of_caller = voice_info_of_caller.channel
        guild = context.message.guild
        guild_player = guild_music_players[guild]
        if voice_channel_of_caller in [client.channel for client in bot.voice_clients]:
            await embed_message(context, "Queue Cleared", ("{0} cleared the song queue..".format(caller.mention,)))
            print("[{0}] cleared the queue in server {1}".format(
                caller, guild.name))
            await guild_player.clear_queue()


@bot.command(name="list", aliases=["l"], brief="List the next songs in the queue.")
async def list(context):
    caller = context.message.author
    guild = context.message.guild
    guild_player = guild_music_players[guild]
    songs_to_list = 5
    song_list = guild_player.list_song_queue(songs_to_list)
    playlist_message = ""
    i = 1
    for song in song_list:
        playlist_message += "{0}. {1}\n".format(i, song.title)
        i += 1
    await embed_message(context, "Current Playlist",
                             (playlist_message+"\n\nThere are currently **{1}** tracks queued."
                                 .format(caller.mention, guild_player.get_queue_size())))


async def embed_message(context, title, message):
    embed = Embed(title=title,
                  description=message,
                  color=Color.blue())
    await context.send(embed=embed)


async def get_song_metadata(search):
    data = await bot.loop.run_in_executor(None, lambda: youtube_info_downloader.extract_info(search, download=False))
    if 'entries' in data:
        data = data['entries'][0]
    return data

bot.run(DISCORD_TOKEN)