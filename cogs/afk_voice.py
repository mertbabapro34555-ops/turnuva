import os
import asyncio
import discord
from discord.ext import commands, tasks

GUILD_ID = int(os.getenv("GUILD_ID", "0"))
VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID", "0"))


class AfkVoice(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.keep_alive_loop.start()

    def cog_unload(self):
        self.keep_alive_loop.cancel()

    async def connect_to_voice(self, channel: discord.VoiceChannel):
        guild = channel.guild
        vc = guild.voice_client

        if vc and vc.is_connected():
            if vc.channel.id != channel.id:
                await vc.move_to(channel)
            return vc

        return await channel.connect(reconnect=True, self_deaf=True)

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            print("[AfkVoice] GUILD_ID hatalı ya da bot bu sunucuda değil.")
            return

        channel = guild.get_channel(VOICE_CHANNEL_ID)
        if channel is None or not isinstance(channel, discord.VoiceChannel):
            print("[AfkVoice] VOICE_CHANNEL_ID hatalı ya da bu bir ses kanalı değil.")
            return

        try:
            await self.connect_to_voice(channel)
            print(f"[AfkVoice] Bağlandım: {channel.name}")
        except Exception as e:
            print(f"[AfkVoice] Bağlanma hatası: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id != self.bot.user.id:
            return
        if after.channel is None:
            guild = self.bot.get_guild(GUILD_ID)
            if guild is None:
                return
            channel = guild.get_channel(VOICE_CHANNEL_ID)
            if channel:
                await asyncio.sleep(2)
                try:
                    await self.connect_to_voice(channel)
                except Exception as e:
                    print(f"[AfkVoice] Yeniden bağlanma hatası: {e}")

    @tasks.loop(minutes=1)
    async def keep_alive_loop(self):
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            return
        channel = guild.get_channel(VOICE_CHANNEL_ID)
        if channel is None:
            return

        vc = guild.voice_client
        if vc is None or not vc.is_connected():
            try:
                await self.connect_to_voice(channel)
                print("[AfkVoice] Ses kanalına yeniden bağlanıldı.")
            except Exception as e:
                print(f"[AfkVoice] Bağlanma hatası: {e}")

    @keep_alive_loop.before_loop
    async def before_keep_alive_loop(self):
        await self.bot.wait_until_ready()

    @commands.command(name="sese_gel")
    @commands.has_permissions(administrator=True)
    async def sese_gel(self, ctx):
        guild = ctx.guild
        channel = guild.get_channel(VOICE_CHANNEL_ID)
        if channel is None:
            await ctx.send("VOICE_CHANNEL_ID ayarlı değil ya da hatalı.")
            return
        await self.connect_to_voice(channel)
        await ctx.send(f"Bağlandım: {channel.name}")

    @commands.command(name="cik")
    @commands.has_permissions(administrator=True)
    async def cik(self, ctx):
        self.keep_alive_loop.cancel()
        vc = ctx.guild.voice_client
        if vc:
            await vc.disconnect()
        await ctx.send("Ses kanalından çıktım.")


async def setup(bot: commands.Bot):
    await bot.add_cog(AfkVoice(bot))
