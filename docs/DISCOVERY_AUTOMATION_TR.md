# YouTube Brain — Otomatik kanal keşfini teşhis etme ve etkinleştirme

## Problem

Ekim 2026 canlı arşiv sorgusu: 100 kanal, 199 video, 1 niş, 1 takip edilen kanal, 578 video istatistik kaydı, 101 kanal istatistik kaydı. Günün ayrı **100 search.list çağrısından 0 kullanılmış**; ortak birim havuzundaki yapılandırılmış 3.000 sınırından yalnızca 2 birim kullanılmış. Bunlar ayrı sayaçlardır.

Bu rakamlar tek başına worker'ın çalışmadığını ispatlamaz. İstatistik yenileme ve kanal keşfi ayrı işlerdir. Kodda `WORKER_QUERIES` varsayılan olarak boştur; bu durumda worker'ın günlük döngüsü konu bazlı yeni kanal keşfi yapmaz. `WORKER_DAILY_INTERVAL_MIN` varsayılanı 1440 dakikadır. Trending listeleri 2025 sonrası çoğunlukla Müzik/Film/Oyun alanlarını kapsar ve Kayıp Sayfalar/1 Dakika İslam için yeterli keşif sağlamaz.

Google'ın güncel resmi kota modeli: arama çağrılarının kendi 100/gün limiti vardır; 1 çağrı 1 arama birimidir. Bu arama bütçesi uygulamadaki ortak 3.000 birim havuzundan farklıdır. Google Cloud'daki gerçek kota ayarlarını da ayrıca kontrol edin; `db_stats` sayacı uygulamanın **yerel kayıtlarından** türetilir.

## Aşama 1: hiçbir API birimi harcamadan teşhis

İkinci VDS'de `root` ile:

```bash
cd /opt/youtube-niche-finder
git fetch --no-tags https://github.com/pixylatte/youtube-niche-finder.git feat/brain-discovery-activation-v9
git show FETCH_HEAD:scripts/diagnose-discovery-readonly.sh | bash -n &&
  bash <(git show FETCH_HEAD:scripts/diagnose-discovery-readonly.sh)
```

Güvenli çıktı: Docker worker `running` mı; `YOUTUBE_API_KEY` **var/yok** (değeri asla gösterilmez); yapılandırılmış konu sayısı; günlük zamanlama; arama sayfası/pencere sayıları; geçmiş döngü işaretleri; yerel kanal, video, niş ve istatistik kayıt sayıları.

## Aşama 2: önce dry-run, sonra bilinçli onay

Worker `running`, API anahtarı `configured` ve Docker Compose kurulumu beklendiği gibiyse:

```bash
python3 <(git show FETCH_HEAD:scripts/configure-discovery-topics.py) \
  "islam tarihi" "osmanlı tarihi" "kayıp uygarlıklar"
```

Bu önizleme **hiçbir şey değiştirmez**. Hedeflenen günlük arama sayısı 3, konu başına 1 sayfa, yalnızca son 7 günün videoları. Gerekirse 1–6 arama konusu verilebilir.

Kullanıcı onayıyla:

```bash
python3 <(git show FETCH_HEAD:scripts/configure-discovery-topics.py) --apply \
  "islam tarihi" "osmanlı tarihi" "kayıp uygarlıklar"
```

`--apply` mevcut `.env` içeriğinin yedeğini `/root/youtube-brain-backups/` altına alır. Yalnızca `WORKER_QUERIES`, `WORKER_QUERY_PERIOD`, `WORKER_QUERY_PAGES`, `WORKER_DAILY_INTERVAL_MIN` değişir; worker konteyneri kontrollü yeniden oluşturulur. PostgreSQL, web, MCP, ve VEVOffice değiştirilmez. Farklı Compose dosyalarıyla başlatılmış worker için işlem engellenir.

**Önemli:** Worker eski `worker_last_daily` zamanına göre davranır. Yeniden başlatmak her zaman anında yeni kanal toplamaz; ilk konu araması bir sonraki günlük döngüde gerçekleşebilir. Komutun kendisi YouTube çağrısı yapmaz; worker'ın sonraki taraması API birimleri harcar. Kalan bütçeyi sınırsız kullanmaya çalışmayın.

## Başarı nasıl ölçülür?

- Sonraki günlük döngüden sonra `db_stats.search_quota.search_calls_today` artmış mı? (Sıfırlama Pasifik saatine göredir.)
- `niches` sayısı 1'den yükselmiş mi?
- `channels` 100'ün üzerine çıkmış mı?
- `videos` ve `history` sayıları artıyor mu?
- Yeni kanal bulunmadıysa bu tek başına arıza değildir: sorgu, zaman penceresi ve tekrarların etkisi incelenmelidir.

Bu operasyon komutları **vidIQ kredisi kullanmaz**. İlk adım sıfır YouTube API kotasıdır; ikinci adımda etkinleştirme sonrası worker'ın planlanan sorguları kota kullanır.
