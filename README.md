# 🏆 1v1 Discord Turnuva + Waitlist + Guard + Ticket + TempVoice Botu

Bu proje; Discord sunucunuzda 1v1 turnuvalar düzenlemenizi, yedek (waitlist) listesini yönetmenizi, geçici 1v1 maç ses kanalları açmanızı, destek talebi (ticket) almanızı ve sunucu güvenliğini (guard) sağlamanızı sağlayan gelişmiş bir Python Discord Botudur.

---

## 🚀 Öne Çıkan Özellikler

1. ⚔️ **1v1 Turnuva & Otomatik Bracket**:
   - `/turnuva-olustur <isim> <max_oyuncu>`: Turnuva kaydı açar.
   - İkişerli kura çekerek 1v1 maçları belirler.
   - Tek kalan oyuncuları otomatik **BAY** geçirtip üst tura taşır.
   - `/skor-gir <mac_id> <kazanan>`: Kazananı belirler, eleneni işaretler ve turu otomatik ilerletir.
   - Şampiyon ilan edildiğinde otomatik görsel kart paylaşır ve istatistikleri kaydeder.

2. 📢 **Otomatik Waitlist (Yedek Listesi)**:
   - Kontenjan dolduğunda katılanlar otomatik **Waitlist** sırasına (Yedek #1, #2...) alınır.
   - Durum anlık olarak **`📢 waitlist`** kanalında güncellenir.
   - Asil kadrodan biri ayrıldığında (`/ayril`), Yedek #1 otomatik asil kadroya geçer ve kullanıcıya Discord bildirimi gider.

3. 🔊 **1v1 Geçici Maç Odaları (Temp Voice)**:
   - Maçlar başladığında bot otomatik olarak **`⚔️ | Oyuncu1 vs Oyuncu2`** adında ses kanalı oluşturur.
   - Maç bitip skor girilince ses kanalı otomatik silinir.

4. 🛡️ **Guard (Sunucu Koruma)**:
   - Anti-Link (Reklam Engelleme)
   - Anti-Spam (Hızlı Mesaj Engelleme)
   - Guard Log bildirim kanalı.

5. 📩 **Ticket (Destek Talebi)**:
   - Butonlu destek paneli.
   - Kişiye özel geçici destek kanalları ve tek tıkla **Transcript (Sohbet Dökümü)** indirme.

6. 🎭 **Oto-Rol & Oyun Seçim Paneli**:
   - Yeni üyelere oto-rol verme.
   - Valorant, LoL, FC24, CS2 gibi oyun rollerini butonla alma.

---

## 🛠️ Kurulum Adımları

### 1. Discord Developer Portal'da Bot Oluşturma
1. [Discord Developer Portal](https://discord.com/developers/applications) adresine gidin.
2. **New Application** butonuna tıklayıp botunuza bir isim verin.
3. Sol menüden **Bot** sekmesine geçin.
4. **Privileged Gateway Intents** altındaki şu 3 izni mutlaka açın:
   - ✅ **PRESENCE INTENT**
   - ✅ **SERVER MEMBERS INTENT**
   - ✅ **MESSAGE CONTENT INTENT**
5. **Reset Token** butonuna basarak Bot Token'ınızı kopyalayın.
6. **OAuth2 -> URL Generator** sekmesinden:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Administrator` (veya Kanal Yönetimi, Rol Yönetimi, Mesaj Gönderme izinleri)
   - Üretilen davet linki ile botu sunucunuza ekleyin.

---

### 2. Yerel Bilgisayarda Çalıştırma

1. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

2. `.env.example` dosyasının adını `.env` olarak değiştirin ve Discord Bot Token'ınızı ekleyin:
   ```env
   DISCORD_BOT_TOKEN=buraya_tokeninizi_yapistirin
   ```

3. Botu başlatın:
   ```bash
   python main.py
   ```

---

## 🌐 7/24 Ücretsiz & Kesintisiz Barındırma (Hosting) Rehberi

Botunuzun bilgisayarınız kapalıyken bile 7/24 çalışması için aşağıdaki yöntemlerden birini kullanabilirsiniz:

### Yöntem A: Railway.app veya Render.com (Ücretsiz / Kolay)
1. Proje klasörünüzü bir **GitHub** reposuna yükleyin (veya Git push yapın).
2. [Railway.app](https://railway.app) veya [Render.com](https://render.com) sitesine üye olun.
3. **New Project -> Deploy from GitHub repo** seçeneğini seçin.
4. Environment Variables (Çevre Değişkenleri) kısmına:
   - `DISCORD_BOT_TOKEN` = `bot_tokeniniz`
   ekleyin.
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `python main.py`
7. Botunuz artık 7/24 bulutta çalışacaktır!

### Yöntem B: VPS / VDS Sunucu (Linux/Ubuntu - PM2 ile)
Sunucunuzda arka planda kesintisiz çalıştırmak için:
```bash
sudo apt update && sudo apt install python3-pip nodejs npm -y
sudo npm install -g pm2
pip install -r requirements.txt

# Botu PM2 ile 7/24 başlatma
pm2 start main.py --name "discord-tournament-bot" --interpreter python3
pm2 save
pm2 startup
```

---

## 📜 Kullanılabilir Slash Komutları

| Komut | Yetki | Açıklama |
| :--- | :--- | :--- |
| `/turnuva-olustur <isim> <max_oyuncu>` | Yönetici | Yeni bir 1v1 turnuva kaydı başlatır. |
| `/turnuva-baslat` | Yönetici | Kayıtları kapatır, kurayı çeker ve 1v1 maçları başlatır. |
| `/skor-gir <mac_id> <kazanan>` | Yönetici | Maçın kazananını belirler ve turu otomatik ilerletir. |
| `/kanallari-ayarla` | Yönetici | Sonuç ve Waitlist kanallarını tanımlar. |
| `/ticket-kur` | Yönetici | Butonlu Destek Paneli kurar. |
| `/guard-ayarla` | Yönetici | Anti-Link ve Anti-Spam korumasını ayarlar. |
| `/rol-paneli-kur` | Yönetici | Butonlu oyun rol paneli kurar. |
| `/oto-rol-ayarla <rol>` | Yönetici | Sunucuya yeni girenlere verilecek rolü ayarlar. |
| `/turnuva-durumu` | Herkes | Aktif turnuva ve maçların durumunu gösterir. |
| `/liderlik-tablosu` | Herkes | En çok 1v1 kazanan ilk 10 oyuncuyu sıralar. |
| `/turnuva-iptal` | Yönetici | Aktif turnuvayı iptal eder. |

---

Bu proje Antigravity AI tarafından sunucunuza özel tasarlanmıştır. Good luck & Have fun! 🎮
