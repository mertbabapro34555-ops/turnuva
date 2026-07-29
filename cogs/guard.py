import discord
from discord.ext import commands
from discord import app_commands
import re
import time

class Guard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_message_times = {}  # {user_id: [timestamp, timestamp, ...]}
        self.link_pattern = re.compile(r'(https?://[^\s]+)|(discord\.gg/[^\s]+)|(discord\.com/invite/[^\s]+)', re.IGNORECASE)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Yönetici izinleri olanları guard es geçer
        if message.author.guild_permissions.administrator or message.author.guild_permissions.manage_messages:
            return

        settings = await self.bot.db.get_guard_settings(message.guild.id)
        if not settings:
            return

        # 1. Anti-Link (Reklam Koruması)
        if settings['anti_link']:
            if self.link_pattern.search(message.content):
                try:
                    await message.delete()
                    await message.channel.send(f"⚠️ {message.author.mention}, sunucuda reklam veya dış bağlantı paylaşımı yasaktır!", delete_after=5)
                    await self.log_guard_action(message.guild, settings['log_channel_id'], "🔗 Anti-Link Engeli", message.author, message.content, message.channel)
                    return
                except Exception:
                    pass

        # 2. Anti-Spam (Hızlı Mesaj Koruması)
        if settings['anti_spam']:
            user_id = message.author.id
            now = time.time()
            if user_id not in self.user_message_times:
                self.user_message_times[user_id] = []
            
            # Son 3 saniyedeki mesajları tut
            self.user_message_times[user_id] = [t for t in self.user_message_times[user_id] if now - t < 3.0]
            self.user_message_times[user_id].append(now)

            if len(self.user_message_times[user_id]) >= 5: # 3 saniyede 5+ mesaj
                try:
                    await message.delete()
                    await message.channel.send(f"🚨 {message.author.mention}, lütfen hızlı mesaj (spam) atmayın!", delete_after=5)
                    await self.log_guard_action(message.guild, settings['log_channel_id'], "⚡ Anti-Spam Engeli", message.author, message.content, message.channel)
                    self.user_message_times[user_id] = []
                    return
                except Exception:
                    pass

    async def log_guard_action(self, guild: discord.Guild, log_channel_id: int, title: str, user: discord.Member, content: str, channel: discord.TextChannel):
        if not log_channel_id:
            return
        log_channel = guild.get_channel(log_channel_id)
        if log_channel:
            embed = discord.Embed(
                title=title,
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Kullanıcı", value=f"{user.mention} ({user.id})", inline=True)
            embed.add_field(name="Kanal", value=channel.mention, inline=True)
            embed.add_field(name="Engellenen İçerik", value=content[:1024] if content else "Yok", inline=False)
            try:
                await log_channel.send(embed=embed)
            except Exception:
                pass

    @app_commands.command(name="guard-ayarla", description="Sunucu koruma (Guard) ayarlarını yapılandırır.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(
        ozellik=[
            app_commands.Choice(name="Anti-Link (Reklam Engeli)", value="anti_link"),
            app_commands.Choice(name="Anti-Spam (Hızlı Mesaj Engeli)", value="anti_spam")
        ],
        durum=[
            app_commands.Choice(name="Açık (Aktif)", value=1),
            app_commands.Choice(name="Kapalı (Pasif)", value=0)
        ]
    )
    async def guard_ayarla(self, interaction: discord.Interaction, ozellik: app_commands.Choice[str], durum: app_commands.Choice[int], log_kanal: discord.TextChannel = None):
        kwargs = {ozellik.value: durum.value}
        if log_kanal:
            kwargs['log_channel_id'] = log_kanal.id

        await self.bot.db.update_guard_settings(interaction.guild.id, **kwargs)
        
        durum_str = "🟢 Açık" if durum.value == 1 else "🔴 Kapalı"
        msg = f"✅ Guard ayarı güncellendi:\n**Özellik**: {ozellik.name}\n**Durum**: {durum_str}"
        if log_kanal:
            msg += f"\n**Log Kanalı**: {log_kanal.mention}"

        await interaction.response.send_message(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Guard(bot))
