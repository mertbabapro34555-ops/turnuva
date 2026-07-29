import discord
from discord.ext import commands
import logging

class TempVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def create_match_voice(self, guild: discord.Guild, player1: discord.Member, player2: discord.Member) -> discord.VoiceChannel:
        """1v1 Maç için iki oyuncuya özel geçici ses kanalı oluşturur."""
        category = discord.utils.get(guild.categories, name="Ses kanalları") or discord.utils.get(guild.categories, name="Organizasyon")
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
            guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True, move_members=True),
        }
        
        if player1:
            overwrites[player1] = discord.PermissionOverwrite(connect=True, speak=True, stream=True)
        if player2:
            overwrites[player2] = discord.PermissionOverwrite(connect=True, speak=True, stream=True)

        channel_name = f"⚔️ | {player1.display_name if player1 else 'BYE'} vs {player2.display_name if player2 else 'BYE'}"
        
        voice_channel = await guild.create_voice_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            user_limit=2
        )
        return voice_channel

    async def delete_match_voice(self, voice_channel: discord.VoiceChannel):
        """Maç bitince ses kanalını güvenle siler."""
        if voice_channel:
            try:
                await voice_channel.delete(reason="Maç tamamlandı.")
            except Exception as e:
                logging.error(f"Ses kanalı silinemedi: {e}")

async def setup(bot):
    await bot.add_cog(TempVoice(bot))
