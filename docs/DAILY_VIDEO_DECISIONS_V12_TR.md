# YouTube Brain v12 — Günlük Video Karar Merkezi (taslak)

## Hedef

"Kayıp Sayfalar için bugün hangi tarih konusunu araştırmalıyız?" ve
"1 Dakika İslam için hangi kısa dinî konuyu araştırmalıyız?" sorularının
cevabını, mevcut Niche Finder arşivindeki video performansına bakarak
**kaynaklı araştırma adayları** biçiminde sunmak.

V12 otomatik olarak yeni video senaryosu, tarihî olay iddiası, ayet/hadis
yorumları veya özgün video başlığı **üretmez**. Arşivden alınan referans
videoların başlığını kullanmak ya da taklit etmek önerilmez.

## Erişim ve davranış

- Menü: **Günlük Video Karar Merkezi** — route \`#/brainNext\`.
- İki editoryal çalışma profili: \`kayip\` (Kayıp Sayfalar) ve \`islam\`
  (1 Dakika İslam). Bunlar doğrulanmış YouTube kanal hesabı değil, iki ayrı
  konu ailesidir. Önceden bulunan \`brainNext v0.1\` fikir kutusu korunur.
- Otomatik araştırma: \`GET /api/daily-decisions?profile=kayip&period=30d&limit=5\`.
- Dönemler \`7d\`, \`30d\`, \`90d\` ile; öneri sayısı 1–8 ile sınırlıdır.
- İlk profil yalnız \`kayıp-sayfalar\` niş önekinden uzun video,
  ikinci profil yalnız \`1-dakika-islam\` niş önekinden Shorts referansı alır.
  Bu etiketler, önceki araştırma arşivinde bizim kullandığımız etiketlerdir.
  Yanlış veya eksik etiketli içerikler bu sürümde kendiliğinden keşfedilmez.
- Adaylar yayın tarihi penceresinden, en az 200 izlenme ve ya kanal bazına
  göre \`outlierScore >= 1.5\` ya da \`viewsPerSubscriber >= 2\` koşuluyla seçilir.
  Bu eşikler **ürün heuristiğidir**, YouTube başarı olasılığı değildir.
- En çok iki video aynı nişten, en çok bir video aynı kanaldan seçilir.
- Yeterli kanıt yoksa \`status=insufficient-data\` ve nedeni döner.
  Boş corpus hiçbir zaman otomatik olarak "talep yok" veya "rekabet az"
  olarak yorumlanmaz.
- Sonuçlar \`referenceTitle\`, orijinal video URL'si, kanal, niş,
  arşivlenen izlenme, outlier ve varsa 24 saatlik hızını gösterir.
  Görsel alıntı, ses klonlama veya materyal indirme yapılmaz.
- Kaynak doğrulama ayrı aşamadır. Tarih için birincil/müze/akademik kaynak,
  dinî bilgiler için ayet, güvenilir hadis kaynakları ve uygun ilmî
  yorumlar doğrulanmadan üretim kararı kesinleştirilmez.

## Güvenlik ve maliyet sınırları

\`application/daily_decisions.py\`, \`domain/daily_decisions.py\`, \`search_outliers\`
ve \`list_niches\` kullanır. Veritabanında salt okunur çalışır. Harici YouTube API
arama, token, OAuth, LLM veya yazma işlemi yapmaz. 16 niş ve niş başına
60 referansla sınırlıdır; 1–8 aday döner. Video URL'si yalnız 11 karakterlik
geçerli YouTube ID'sinden türetilir; UI metinleri escape edilir.

Performans sonuçları, arşiv kapsamının yansımasıdır; canlı trend veya
bağımsız tarih/din doğrulaması değildir. İstatistik yetersizliği varsa
VPH üretilmez ve panel boş veri uydurmaz.

## Test ve yayın sırası

V12 taslağı v11 üzerine, v11 v10 üzerine, v10 v9 üzerine kuruludur.
Bu yığılmış GitHub dalları henüz canlıya otomatik geçirilmez.

1. Ruff + Python testleri + HTTP API doküman üretimi
2. Ayrı PostgreSQL test şemasıyla Chromium ekran açılışı
3. Gerçek v9 worker keşif durumunu salt okunur doğrulama
4. İncelemeden sonra kontrollü yayın

CI veya izole önizleme raporu oluşana kadar "PASS" ya da "canlıda çalışıyor"
iddiası yapılmaz. Canlı Nginx, Docker, VDS, API anahtarı ve database
yapısı değiştirilmedi.
