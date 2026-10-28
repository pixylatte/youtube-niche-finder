# YouTube Brain v13 — Özgün İçerik ve Editoryal Hazırlık Kontrolü

## Kullanıcı akışı

1. **Günlük Video Karar Merkezi** (\`#/brainNext\`) açılır; iki çalışma profilinden biri seçilir.
2. Mevcut arşivdeki video performansı, rakip kanal ve araştırma alanı gösterilir.
3. Her adayda **Özgün fikir ve kaynak kontrolü** seçeneği, aynı sayfada düzenleme formunu açar.
4. Kullanıcı referans başlığını kopyalamadan farklı bir soru/anlatım açısı yazar.
5. En çok 3 kaynak URL'si (API en fazla 6) girilir; kaynağın türü ve kullanıcının
   okuyup okumadığı işaretlenir.
6. Tarih için arşiv/müze/akademik/resmî kaynak; İslam için Kur'an/hadis/ilmî
   kaynak sınıflarından en az biri, iki ayrı URL alan adı ve insan inceleme beyanı
   gerekir. Görsel/ses lisansı ve üretim zorluğu ayrıca işaretlenir.
7. Sistem eksik aşamaları gösterir. "İnsan editör incelemesine hazırlanmış"
   yalnızca **formun kullanıcı beyanlarıyla tamamlandığı** anlamına gelir;
   yayın onayı veya otomatik doğrulama DEĞİLDİR.

## Kanıt ve dürüstlük sınırı

- Rakip örneklemi = Niche Finder'ın mevcut arşivinden ilgili etiket ve video
  biçiminde çekilmiş **en fazla 60 video × niş**, tüm YouTube pazarı değildir.
- Rakip başlığı, ayrı tarihî/dinî bilgi kaynağı sayılmaz. YouTube/TikTok/Instagram
  alan adları bu yüzden insanın faktüel kaynak sayısına dahil edilmez.
- Kullanıcının girdiği \`source.type\` ve \`reviewed\` bayrakları **beyandır**.
  DNS, URL erişimi, belgenin içeriği, hadisin sıhhati, tarihî doğruluk,
  telif/lisans veya üçüncü taraf izinleri sunucu tarafından doğrulanmaz.
- Sunucu yanıtında \`sourcesVerifiedExternally: false\`,
  \`factsVerifiedExternally: false\`, \`rightsClearedBySystem: false\` her zaman
  açıkça bulunur.
- Rakip videosunun performansı video fikrinin başarısını veya teolojik/tarihsel
  iddianın doğruluğunu garanti etmez.
- Özgünlük kontrolü yalnız asgari metin/kelime karşılaştırmasıdır. Telif veya
  özgün eser değerlendirmesinin yerini tutmaz.

## API sözleşmesi

\`POST /api/editorial/readiness\` — ücretsiz ve salt hesaplamalıdır.
Örnek gövde:

\`\`\`json
{
  "profile": "kayip",
  "referenceTitle": "Arşivden örnek video başlığı",
  "angle": "İki bağımsız arşiv belgesi arasındaki anlatım farklarını incelemek",
  "effort": "medium",
  "claimsReviewed": true,
  "rightsReviewed": true,
  "sources": [
    {"url": "https://example.gov.tr/document", "type": "archive", "reviewed": true},
    {"url": "https://example.edu.tr/article", "type": "academic", "reviewed": true}
  ]
}
\`\`\`

Bu bağlantılar örnektir, doğrulanmış gerçek kaynak değildir.
Yanıt \`research-incomplete\` veya
\`prepared-for-human-editorial-review\` döndürür; tamamlanmamış kriterler
\`blockers\` alanında tek tek yer alır. Kaynakların URL yolunu, gizli
bilgileri ve açı metnini yanıtına tekrar eklemez. HTTPS dışındaki bağlantılar,
giriş bilgisi taşıyan URL'ler, IP adresleri reddedilir.

## Kalıcılık / izolasyon

Form yalnız sayfanın geçerli durumundadır. Veri PostgreSQL'e, sunucu diske
veya tarayıcı localStorage'a yazılmaz; sayfa yenilenince kaybolur. Gizli
bilgiler, abonelik token'ları, API anahtarları ve özel belgeler bu forma
konulmamalıdır. Durum yalnız mevcut kullanıcıya gösterilir.

Yeni endpoint, yeni YouTube araması, LLM, OAuth veya veri toplama işlemi
başlatmaz. Hiçbir canlı VDS, PostgreSQL, Docker worker veya Nginx
konfigürasyonu değiştirilmez.

## İnceleme ve test durumu

- \`test_editorial_readiness_domain.py\`: kaynak/özgünlük/hak/URL kontrolleri.
- \`test_daily_decisions_domain.py\`: örneklem kapsamını uydurma pazar puanıyla
  karıştırmama.
- \`test_http_api.py\`: ücretsiz HTTP uç noktası ve hata sözleşmesi.
- \`frontend/tests/test_smoke.py\`: gerçek Chrome/Playwright ile örnek adaydan
  kaynak formuna kadar iki aşamalı senaryo (synthetic archive candidate).
- GitHub CI ve izole Playwright çalıştırması tamamlanmadan **PASS denemez**.
- v13, v12 üzerine taslak PR; v12 / v11 / v10 / v9 zinciri henüz canlıya
  geçirilmedi. Yayın onayı ayrı operasyonel kapıda verilir.
