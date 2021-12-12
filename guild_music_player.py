import asyncio
from discord import Embed, Color, FFmpegPCMAudio
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

    FF_MPEG = os.getenv("ffmpeg_exe")

    def __init__(self, guild, bot):
        self.guild = guild
        self.bot = bot
        self.song_queue = asyncio.Queue()
        self.next_song_event = asyncio.Event()

    def get_queue_size(self):
        return self.song_queue.qsize()

    async def clear_queue(self):
        while not self.song_queue.empty():
            await self.song_queue.get()

    async def queue_song(self, context, song_metadata):
        title = song_metadata['title']
        source = song_metadata['formats'][0]['url']
        await self.song_queue.put(Song(context, title, source, context.message.author))

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
            voice_client.play(FFmpegPCMAudio(
                executable=self.FF_MPEG, source=song.source), after=self.go_to_next_song)
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
