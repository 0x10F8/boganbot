from discord import Embed, Color
from discord.ext.commands import Bot
from discord.ext.commands.core import Command
from guild_music_player import GuildMusicPlayer
import youtube_dl


class BoganBot(Bot):
    guild_music_players = {}
    youtube_info_downloader = youtube_dl.YoutubeDL({
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    })

    def __init__(self, command_prefix="!"):
        super().__init__(command_prefix)
        self.add_command(Command(self.join, name="join", pass_context=True))
        self.add_command(Command(self.play, name="play", pass_context=True))
        self.add_command(Command(self.skip, name="skip", pass_context=True))
        self.add_command(Command(self.clear, name="clear", pass_context=True))

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
        voice_info = context.message.author.voice
        guild = context.message.guild
        connected = False
        if not voice_info:
            await context.send("{0} you need to be in a voice channel for the bot to join.")
        else:
            voice_channel = voice_info.channel
            if not guild.voice_client or \
                    (guild.voice_client and not guild.voice_client.is_connected()):
                await voice_channel.connect()
            connected = True
        return connected

    async def play(self, context):
        if await self.join(context):
            guild = context.message.guild
            argument_string = context.message.content.replace(
                context.prefix+context.command.name+" ", "")
            if argument_string is not None and len(argument_string.strip()) > 0:
                song_metadata = await self.get_song_metadata(argument_string)
                songname = song_metadata['title']
                caller = context.message.author
                guild_player = self.guild_music_players[guild]
                await self.embed_message(context, "Song Queued",
                                         ("{0} queued {1}.\n\nThere are currently **{2}** tracks queued."
                                          .format(caller.mention, songname, guild_player.get_queue_size())))
                print("[{0}] queued up {1} with '{2}' for server [{3}]".format(
                    caller, songname, argument_string, guild.name))
                await guild_player.queue_song(context, song_metadata)

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
