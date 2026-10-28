# YouTube Brain — Keşif Aktivitesi ve Kota Kanıtı (v10, taslak)

Bu değişiklik, **Veriler** ekranında yalnız yerel veritabanı metaverilerini
okuyarak iki zamanlayıcı işaretini ve iki kota havuzunu yan yana gösterir.

- \`worker_last_daily\` ve \`worker_last_topic_search\`, worker'ın kaydettiği
  **zamanlayıcı işaretleridir**. Başarılı YouTube araması, yaşayan Docker
  worker'ı ya da yeni kanal bulunduğu anlamına **gelmez**. Worker'ın \`_safe\`
  çağrısı başarısız olsa bile günlük işaret yazılabilir.
- \`search_calls_today\`: Pasifik gününe göre kaydedilen YouTube arama
  çağrıları; MCP üzerinden elle yapılan aramaları da kapsar.
- \`units_today\`: Yapılandırılmış ortak API havuzundan kaydedilen kullanımlar.
- Son işaret 48 saatten eskiyse **eski**, yoksa **yok**, bozuksa **geçersiz**
  olarak görünür. İleri saat farkı ayrı işaretlenir.
- Veri yoksa \`0\` gibi gösterilmez. Zaman damgasının yokluğu başarısızlık
  teşhisi değildir.
- \`GET /api/discovery-activity\`: oturum gerektiren, **salt-okunur** uç nokta.
  Yeni YouTube isteği, Docker etkileşimi, yeniden başlatma veya DB yazımı yok.
  Çok kullanıcılı kurulumda mevcut oturum middleware'i geçerlidir.

**Önemli:** v9 \`scripts/diagnose-discovery-readonly.sh\` ile canlı Docker
worker'ın gerçek durumu ve \`WORKER_QUERIES\` yapılandırması ayrıca doğrulanır.
Bu v10 ekranı onların yerine geçmez.

Değişiklik, \`feat/brain-discovery-activation-v9\` üstüne **Draft PR** olarak
hazırlanır. Test/CI ve izole önizleme kanıtı olmadan PASS veya canlı dağıtım
iddiası yoktur. Ana dal, ikinci VDS, çalışan worker, PostgreSQL ve API anahtarı
değiştirilmez.
