import asyncio
from discord import Embed, Color, FFmpegOpusAudio
import dotenv
import os

dotenv.load_dotenv()


class Song:

    def __init__(self, context, title, source, queue_by):
        self.context = context
        self.title = title
        self.source = source
        self.queued_by = queue_by


class GuildMusicPlayer:

    FF_MPEG = os.getenv("FFMPEG")

    def __init__(self, guild, bot):
        self.guild = guild
        self.bot = bot
        self.song_queue = asyncio.Queue()
        self.next_song_event = asyncio.Event()

    def get_queue_size(self):
        return self.song_queue.qsize()

    def list_song_queue(self, no_of_tracks=5):
        i = 0
        song_list = []
        for item in list(self.song_queue._queue):
            i += 1
            song_list.append(item)
            if i >= no_of_tracks:
                break
        return song_list

    async def clear_queue(self):
        while not self.song_queue.empty():
            await self.song_queue.get()

    def find_best_audio_source(self, song_metadata):
        source = None
        asr = -1
        for song_format in song_metadata['formats']:
            if "asr" in song_format.keys() and song_format['asr'] is not None and song_format['asr'] > asr and song_format['acodec'] == 'opus':
                source = song_format['url']
        return source

    async def queue_song(self, context, song_metadata):
        title = song_metadata['title']
        source = self.find_best_audio_source(song_metadata)
        if source is not None:
            await self.song_queue.put(Song(context, title, source, context.message.author))
        else:
            await self.embed_message(context, "Sorry", "Sorry {0} there was an issue loading the song {1}".format(context.message.author.mention, title))

    async def play_next_song(self):
        while True:
            self.next_song_event.clear()
            song = await self.song_queue.get()
            voice_client = song.context.guild.voice_client
            print("Playing [{0}] in [{1}]".format(
                song.title, self.guild.name))
            await self.embed_message(song.context, "Now Playing...",
                                     "Now playing {0} - queued by {1}.\n\nThere are currently **{2}** tracks queued."
                                     .format(song.title, song.queued_by.mention, self.get_queue_size()))
            FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
            voice_client.play(
                FFmpegOpusAudio(executable=self.FF_MPEG, source=song.source, **FFMPEG_OPTS),
                after=self.go_to_next_song)
            await self.next_song_event.wait()

    async def embed_message(self, context, title, message):
        embed = Embed(title=title,
                      description=message,
                      color=Color.blue())
        await context.send(embed=embed)

    def go_to_next_song(self, error=None):
        print("Next song on server [{0}]".format(self.guild.name))
        if error is not None:
            print("There was an error during the last song on the [{0}] server: {1}".format(
                self.guild.name, error))
        self.bot.loop.call_soon_threadsafe(self.next_song_event.set)
