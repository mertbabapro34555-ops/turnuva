import discord
from discord.ext import commands
from discord import app_commands
import random
import math
import logging

class TournamentJoinView(discord.ui.View):
    def __init__(self, bot, tournament_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.tournament_id = tournament_id

    @discord.ui.button(label="🏆 Turnuvaya Katıl", style=discord.ButtonStyle.success, custom_id="tr_join_btn")
    async def join_tournament(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog("Tournament")
        if cog:
            await cog.handle_join(interaction, self.tournament_id)

    @discord.ui.button(label="❌ Ayrıl", style=discord.ButtonStyle.danger, custom_id="tr_leave_btn")
    async def leave_tournament(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog("Tournament")
        if cog:
            await cog.handle_leave(interaction, self.tournament_id)

    @discord.ui.button(label="📋 Katılımcı Listesi", style=discord.ButtonStyle.secondary, custom_id="tr_list_btn")
    async def list_participants(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog("Tournament")
        if cog:
            await cog.handle_list(interaction, self.tournament_id)


class Tournament(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Active view reload helper if needed
        pass

    # --- KANAL AYARLARI ---
    @app_commands.command(name="kanallari-ayarla", description="Turnuva sonuç ve waitlist kanallarını belirler.")
    @app_commands.checks.has_permissions(administrator=True)
    async def kanallari_ayarla(self, interaction: discord.Interaction, sonuclar_kanali: discord.TextChannel = None, waitlist_kanali: discord.TextChannel = None):
        kwargs = {}
        if sonuclar_kanali:
            kwargs['results_channel_id'] = sonuclar_kanali.id
        if waitlist_kanali:
            kwargs['waitlist_channel_id'] = waitlist_kanali.id

        if kwargs:
            await self.bot.db.set_config(interaction.guild.id, **kwargs)
            await interaction.response.send_message("✅ Turnuva kanalları başarıyla kaydedildi!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ En az bir kanal seçmelisiniz.", ephemeral=True)

    # --- TURNUVA OLUŞTURMA ---
    @app_commands.command(name="turnuva-olustur", description="Yeni bir 1v1 turnuva kaydı başlatır.")
    @app_commands.checks.has_permissions(administrator=True)
    async def turnuva_olustur(self, interaction: discord.Interaction, isim: str, max_oyuncu: int):
        active = await self.bot.db.get_active_tournament(interaction.guild.id)
        if active:
            await interaction.response.send_message(f"❌ Zaten aktif bir turnuva mevcut: **{active['name']}** (Durum: {active['status']})", ephemeral=True)
            return

        tr_id = await self.bot.db.create_tournament(interaction.guild.id, isim, max_oyuncu)

        embed = discord.Embed(
            title=f"🏆 1v1 TURNUVA: {isim}",
            description=f"Turnuva kayıtları açılmıştır!\n\n**Kontenjan**: {max_oyuncu} Oyuncu\nKontenjan dolduğunda katılanlar **📢 Waitlist (Yedek)** listesine alınır.",
            color=discord.Color.gold()
        )
        embed.add_field(name="Nasıl Katılırım?", value="Aşağıdaki **🏆 Turnuvaya Katıl** butonuna tıklayarak kaydolabilirsiniz.", inline=False)
        embed.set_footer(text=f"Turnuva ID: #{tr_id} | Sunucu 1v1 Şampiyonası")

        await interaction.response.send_message("✅ Turnuva başarıyla oluşturuldu ve duyuruldu!", ephemeral=True)
        msg = await interaction.channel.send(embed=embed, view=TournamentJoinView(self.bot, tr_id))
        
        # Waitlist kanalını güncelle
        await self.update_waitlist_embed(interaction.guild, tr_id)

    # --- KATILMA / AYRILMA İŞLEYİCİLERİ ---
    async def handle_join(self, interaction: discord.Interaction, tournament_id: int):
        tr = await self.bot.db.get_active_tournament(interaction.guild.id)
        if not tr or tr['id'] != tournament_id or tr['status'] != 'registration':
            await interaction.response.send_message("❌ Bu turnuva için kayıtlar kapalı veya turnuva başlamış.", ephemeral=True)
            return

        existing = await self.bot.db.get_participant(tournament_id, interaction.user.id)
        if existing:
            durum_str = "Asil Kadro" if existing['status'] == 'active' else f"Yedek Listesi (#{existing['waitlist_order']})"
            await interaction.response.send_message(f"❌ Zaten turnuvaya kayıtlısınız! Durumunuz: **{durum_str}**", ephemeral=True)
            return

        active_participants = await self.bot.db.get_participants(tournament_id, status='active')
        waitlist_participants = await self.bot.db.get_participants(tournament_id, status='waitlist')

        if len(active_participants) < tr['max_players']:
            # Asil kadroya ekle
            await self.bot.db.add_participant(tournament_id, interaction.user.id, interaction.user.display_name, status='active')
            await interaction.response.send_message(f"🎉 **{tr['name']}** turnuvasına **Asil Kadrodan** katıldınız! ({len(active_participants)+1}/{tr['max_players']})", ephemeral=True)
        else:
            # Waitlist (Yedek) sırasına ekle
            next_order = len(waitlist_participants) + 1
            await self.bot.db.add_participant(tournament_id, interaction.user.id, interaction.user.display_name, status='waitlist', waitlist_order=next_order)
            await interaction.response.send_message(f"📢 Kontenjan dolu olduğu için **Yedek Listesine** alındınız. **Yedek Sıranız: #{next_order}**", ephemeral=True)

        await self.update_waitlist_embed(interaction.guild, tournament_id)

    async def handle_leave(self, interaction: discord.Interaction, tournament_id: int):
        existing = await self.bot.db.get_participant(tournament_id, interaction.user.id)
        if not existing:
            await interaction.response.send_message("❌ Zaten bu turnuvada kayıtlı değilsiniz.", ephemeral=True)
            return

        was_active = (existing['status'] == 'active')
        await self.bot.db.remove_participant(tournament_id, interaction.user.id)

        msg = " Turnuvadan ayrıldınız."

        # Eğer ayrılan kişi asil kadrodaysa ve yedekte bekleyen varsa, ilk yedeği asil kadroya al!
        if was_active:
            promoted = await self.bot.db.promote_first_waitlist(tournament_id)
            if promoted:
                msg += f"\n🎉 Sıranız boşaldığı için yedekteki **{promoted['user_name']}** asil kadroya yükseltildi!"
                # Yükseltilen oyuncuya DM veya bildirim gönder
                try:
                    member = interaction.guild.get_member(promoted['user_id'])
                    if member:
                        await member.send(f"🎉 Müjde! Turnuvadan bir oyuncu ayrıldığı için **Asil Kadroya** alındınız! Hazır olun!")
                except Exception:
                    pass

        await interaction.response.send_message(msg, ephemeral=True)
        await self.update_waitlist_embed(interaction.guild, tournament_id)

    async def handle_list(self, interaction: discord.Interaction, tournament_id: int):
        active_p = await self.bot.db.get_participants(tournament_id, status='active')
        wait_p = await self.bot.db.get_participants(tournament_id, status='waitlist')

        embed = discord.Embed(title="📋 Turnuva Katılımcı Listesi", color=discord.Color.blue())
        
        active_str = "\n".join([f"{i+1}. <@{p['user_id']}>" for i, p in enumerate(active_p)]) if active_p else "Henüz katılan yok."
        wait_str = "\n".join([f"#{p['waitlist_order']} <@{p['user_id']}>" for p in wait_p]) if wait_p else "Yedekte bekleyen yok."

        embed.add_field(name=f"⚔️ Asil Kadro ({len(active_p)})", value=active_str, inline=False)
        embed.add_field(name=f"📢 Yedek Listesi ({len(wait_p)})", value=wait_str, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def update_waitlist_embed(self, guild: discord.Guild, tournament_id: int):
        """📢 waitlist kanalına güncel liste kartını gönderir/günceller."""
        config = await self.bot.db.get_config(guild.id)
        if not config or not config['waitlist_channel_id']:
            return

        w_channel = guild.get_channel(config['waitlist_channel_id'])
        if not w_channel:
            return

        tr = await self.bot.db.get_active_tournament(guild.id)
        if not tr:
            return

        active_p = await self.bot.db.get_participants(tournament_id, status='active')
        wait_p = await self.bot.db.get_participants(tournament_id, status='waitlist')

        embed = discord.Embed(
            title=f"📢 CANLI WAITLIST & KATILIM | {tr['name']}",
            description=f"**Doluluk**: {len(active_p)}/{tr['max_players']} Asil Oyuncu | **Yedek**: {len(wait_p)} Oyuncu",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        active_list = "\n".join([f"🟢 {i+1}. <@{p['user_id']}>" for i, p in enumerate(active_p)]) if active_p else "Katılımcı yok."
        wait_list = "\n".join([f"⏳ **Yedek #{p['waitlist_order']}**: <@{p['user_id']}>" for p in wait_p]) if wait_p else "Yedek listesi boş."

        embed.add_field(name="⚔️ Asil Oyuncular", value=active_list[:1024], inline=False)
        embed.add_field(name="⏳ Yedek Bekleme Sırası", value=wait_list[:1024], inline=False)

        try:
            # Son mesajı bulup güncelle veya yeni mesaj at
            messages = [m async for m in w_channel.history(limit=5)]
            bot_msg = next((m for m in messages if m.author == self.bot.user and m.embeds and "CANLI WAITLIST" in m.embeds[0].title), None)
            if bot_msg:
                await bot_msg.edit(embed=embed)
            else:
                await w_channel.send(embed=embed)
        except Exception as e:
            logging.error(f"Waitlist embed güncellenirken hata: {e}")

    # --- TURNUVA BAŞLATMA & EŞLEŞTİRME ---
    @app_commands.command(name="turnuva-baslat", description="Turnuva kayıtlarını kapatır ve 1v1 eşleşmeleri başlatır.")
    @app_commands.checks.has_permissions(administrator=True)
    async def turnuva_baslat(self, interaction: discord.Interaction):
        tr = await self.bot.db.get_active_tournament(interaction.guild.id)
        if not tr or tr['status'] != 'registration':
            await interaction.response.send_message("❌ Başlatılabilecek kayıt aşamasında bir turnuva yok.", ephemeral=True)
            return

        active_participants = await self.bot.db.get_participants(tr['id'], status='active')
        if len(active_participants) < 2:
            await interaction.response.send_message("❌ Turnuvayı başlatmak için en az 2 asil oyuncu gereklidir!", ephemeral=True)
            return

        await interaction.response.defer()

        # Oyuncuları karıştır (Kura)
        players = list(active_participants)
        random.shuffle(players)

        round_num = 1
        await self.bot.db.update_tournament_status(tr['id'], 'active', current_round=round_num)

        temp_voice_cog = self.bot.get_cog("TempVoice")

        matches_summary = []
        match_num = 1

        # 1v1 Çiftleştirme
        for i in range(0, len(players), 2):
            p1 = players[i]
            p2 = players[i+1] if (i+1) < len(players) else None

            m1 = interaction.guild.get_member(p1['user_id'])
            m2 = interaction.guild.get_member(p2['user_id']) if p2 else None

            voice_chan = None
            if temp_voice_cog and m1 and m2:
                voice_chan = await temp_voice_cog.create_match_voice(interaction.guild, m1, m2)

            v_id = voice_chan.id if voice_chan else None
            match_id = await self.bot.db.create_match(tr['id'], round_num, match_num, p1['user_id'], p2['user_id'] if p2 else None, temp_voice_id=v_id)

            if p2 is None:
                # Tek kalan kişi BAY geçer (Direkt üst tura geçer)
                await self.bot.db.set_match_winner(match_id, p1['user_id'])
                matches_summary.append(f"🔹 **Maç #{match_id}**: <@{p1['user_id']}> ➡️ **BAY Geçti (Otomatik Üst Tur)**")
            else:
                voice_str = f" ({voice_chan.mention})" if voice_chan else ""
                matches_summary.append(f"⚔️ **Maç #{match_id}**: <@{p1['user_id']}> VS <@{p2['user_id']}>{voice_str}")

            match_num += 1

        embed = discord.Embed(
            title=f"🔥 {tr['name']} - TUR 1 EŞLEŞMELERİ BAŞLADI!",
            description="1v1 Turnuva maçları çekilen kura ile belirlenmiştir.\nMaç bittiğinde yetkililer `/skor-gir <mac_id> <kazanan>` komutu ile sonucu girecektir.",
            color=discord.Color.red()
        )
        embed.add_field(name="Tur 1 Maçları", value="\n".join(matches_summary), inline=False)
        embed.set_footer(text="Maçını tamamlayan oyuncular ses kanallarında hazır beklemelidir.")

        await interaction.followup.send(embed=embed)

    # --- SKOR GİRME & TUR ATLAMA ---
    @app_commands.command(name="skor-gir", description="Bir 1v1 maçın kazananını belirler ve turu ilerletir.")
    @app_commands.checks.has_permissions(administrator=True)
    async def skor_gir(self, interaction: discord.Interaction, mac_id: int, kazanan: discord.Member):
        match = await self.bot.db.get_match_by_id(mac_id)
        if not match:
            await interaction.response.send_message("❌ Belirtilen ID ile maç bulunamadı.", ephemeral=True)
            return

        if match['status'] == 'completed':
            await interaction.response.send_message("❌ Bu maç zaten tamamlanmış!", ephemeral=True)
            return

        if kazanan.id not in (match['player1_id'], match['player2_id']):
            await interaction.response.send_message("❌ Kazanan olarak belirttiğiniz kişi bu maçın oyuncularından biri değil!", ephemeral=True)
            return

        await self.bot.db.set_match_winner(mac_id, kazanan.id)

        # Maç ses kanalını sil
        if match['temp_voice_id']:
            v_chan = interaction.guild.get_channel(match['temp_voice_id'])
            temp_voice_cog = self.bot.get_cog("TempVoice")
            if temp_voice_cog and v_chan:
                await temp_voice_cog.delete_match_voice(v_chan)

        await interaction.response.send_message(f"🏆 Maç #{mac_id} sonucu kaydedildi! Kazanan: {kazanan.mention}", ephemeral=False)

        # Sonuçlar kanalına duyur
        config = await self.bot.db.get_config(interaction.guild.id)
        if config and config['results_channel_id']:
            r_chan = interaction.guild.get_channel(config['results_channel_id'])
            if r_chan:
                r_embed = discord.Embed(
                    title=f"⚔️ MAÇ SONUCU | Maç #{mac_id}",
                    description=f"**Kazanan**: {kazanan.mention} 🎉\nBir sonraki tura yükseldi!",
                    color=discord.Color.green()
                )
                await r_chan.send(embed=r_embed)

        # Tur tamamlandı mı kontrol et
        await self.check_and_advance_round(interaction, match['tournament_id'], match['round'])

    async def check_and_advance_round(self, interaction: discord.Interaction, tournament_id: int, current_round: int):
        matches = await self.bot.db.get_matches_for_round(tournament_id, current_round)
        pending = [m for m in matches if m['status'] == 'pending']

        if len(pending) > 0:
            # Tur henüz tamamlanmadı
            return

        # Tur tamamlandı! Kazananları topla
        winners = [m['winner_id'] for m in matches if m['winner_id'] is not None]

        if len(winners) == 1:
            # ŞAMPİYON BELLİ OLDU!
            champion_id = winners[0]
            champion = interaction.guild.get_member(champion_id)
            await self.bot.db.update_tournament_status(tournament_id, 'completed')
            await self.bot.db.record_tournament_win(champion_id)

            champ_embed = discord.Embed(
                title="🏆 TURNUVA ŞAMPİYONU İLAN EDİLDİ!",
                description=f"Tebrikler <@{champion_id}>! 1v1 Turnuvayı birincilikle tamamlayarak **ŞAMPİYON** oldun! 👑",
                color=discord.Color.gold()
            )
            champ_embed.set_thumbnail(url=champion.display_avatar.url if champion else None)
            
            await interaction.channel.send(embed=champ_embed)

            # Sonuçlar kanalına at
            config = await self.bot.db.get_config(interaction.guild.id)
            if config and config['results_channel_id']:
                r_chan = interaction.guild.get_channel(config['results_channel_id'])
                if r_chan:
                    await r_chan.send(embed=champ_embed)
            return

        if len(winners) > 1:
            # Yeni Tur Başlat!
            next_round = current_round + 1
            await self.bot.db.update_tournament_status(tournament_id, 'active', current_round=next_round)

            random.shuffle(winners)
            temp_voice_cog = self.bot.get_cog("TempVoice")

            next_matches_summary = []
            match_num = 1

            for i in range(0, len(winners), 2):
                p1_id = winners[i]
                p2_id = winners[i+1] if (i+1) < len(winners) else None

                m1 = interaction.guild.get_member(p1_id)
                m2 = interaction.guild.get_member(p2_id) if p2_id else None

                voice_chan = None
                if temp_voice_cog and m1 and m2:
                    voice_chan = await temp_voice_cog.create_match_voice(interaction.guild, m1, m2)

                v_id = voice_chan.id if voice_chan else None
                m_id = await self.bot.db.create_match(tournament_id, next_round, match_num, p1_id, p2_id, temp_voice_id=v_id)

                if p2_id is None:
                    await self.bot.db.set_match_winner(m_id, p1_id)
                    next_matches_summary.append(f"🔹 **Maç #{m_id}**: <@{p1_id}> ➡️ **BAY Geçti**")
                else:
                    voice_str = f" ({voice_chan.mention})" if voice_chan else ""
                    next_matches_summary.append(f"⚔️ **Maç #{m_id}**: <@{p1_id}> VS <@{p2_id}>{voice_str}")

                match_num += 1

            embed = discord.Embed(
                title=f"🔥 TUR {next_round} EŞLEŞMELERİ BAŞLADI!",
                description="Kalan oyuncular arasında yeni tur 1v1 maçları başladı!",
                color=discord.Color.purple()
            )
            embed.add_field(name=f"Tur {next_round} Maçları", value="\n".join(next_matches_summary), inline=False)
            await interaction.channel.send(embed=embed)

    # --- DURUM & LİDERLİK TABLOSU ---
    @app_commands.command(name="turnuva-durumu", description="Aktif turnuvanın ve mevcut tur maçlarının durumunu gösterir.")
    async def turnuva_durumu(self, interaction: discord.Interaction):
        tr = await self.bot.db.get_active_tournament(interaction.guild.id)
        if not tr:
            await interaction.response.send_message("❌ Şu anda aktif bir turnuva yok.", ephemeral=True)
            return

        matches = await self.bot.db.get_matches_for_round(tr['id'], tr['current_round'])
        embed = discord.Embed(
            title=f"📊 TURNUVA DURUMU | {tr['name']}",
            description=f"**Mevcut Aşama**: Tur {tr['current_round']} ({tr['status'].upper()})",
            color=discord.Color.blue()
        )

        if matches:
            m_list = []
            for m in matches:
                p1 = f"<@{m['player1_id']}>" if m['player1_id'] else "Yok"
                p2 = f"<@{m['player2_id']}>" if m['player2_id'] else "Yok"
                status_str = f"🏆 Kazanan: <@{m['winner_id']}>" if m['status'] == 'completed' else "⏳ Oynanıyor"
                m_list.append(f"**Maç #{m['id']}**: {p1} VS {p2} ➡️ {status_str}")
            embed.add_field(name=f"Tur {tr['current_round']} Maçları", value="\n".join(m_list), inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="liderlik-tablosu", description="En çok turnuva ve 1v1 galibiyeti alan oyuncuları listeler.")
    async def liderlik_tablosu(self, interaction: discord.Interaction):
        top_players = await self.bot.db.get_top_players(limit=10)
        if not top_players:
            await interaction.response.send_message("Henüz kayıtlı bir sıralama istatistiği yok.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🥇 1v1 TURNUVA LİDERLİK TABLOSU",
            description="Sunucudaki en başarılı 1v1 oyuncuları:",
            color=discord.Color.gold()
        )

        medals = ["🥇", "🥈", "🥉"]
        rows = []
        for idx, p in enumerate(top_players):
            icon = medals[idx] if idx < 3 else f"**#{idx+1}**"
            rows.append(f"{icon} <@{p['user_id']}> 🏆 **{p['tournaments_won']} Şampiyonluk** | ⚔️ {p['wins']} Galibiyet / {p['losses']} Mağlubiyet")

        embed.description += "\n\n" + "\n".join(rows)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="turnuva-iptal", description="Aktif turnuvayı iptal eder.")
    @app_commands.checks.has_permissions(administrator=True)
    async def turnuva_iptal(self, interaction: discord.Interaction):
        tr = await self.bot.db.get_active_tournament(interaction.guild.id)
        if not tr:
            await interaction.response.send_message("❌ İptal edilecek aktif turnuva yok.", ephemeral=True)
            return

        await self.bot.db.update_tournament_status(tr['id'], 'cancelled')
        await interaction.response.send_message(f"🚫 **{tr['name']}** turnuvası iptal edildi.", ephemeral=False)

async def setup(bot):
    await bot.add_cog(Tournament(bot))
