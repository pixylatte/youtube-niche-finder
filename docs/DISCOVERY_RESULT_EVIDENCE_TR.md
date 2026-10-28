# YouTube Brain — Gerçek Keşif Sonuçları (v11, taslak)

## Ne değişti?

v10 yalnız zamanlayıcı işaretlerini ve genel kota sayaçlarını gösteriyordu.
Bir zamanlayıcı işaretinin bulunması YouTube aramasının çalıştığının
kanıtı değildir. v11 worker içindeki `WORKER_QUERIES` taramasının en son
**gerçek fonksiyon dönüşlerini** sayarak yerel veritabanının
`worker_discovery_last_run` meta anahtarına özet yazar.

Bu veri, önceki yalnızca okumaya dayalı v10 API'si üzerinden güvenli biçimde
okunur: `GET /api/discovery-activity`. Yeni API çağrısı, yeni tablo veya
YouTube API kotası tüketimi yoktur.

## Kaydedilen alanlar

- `at`: tamamlanan planlanmış toplama döngüsünün zamanı (UTC)
- `configuredTopics`: o döngüde yapılandırılmış konu sayısı
- `attempted`: gerçekten çağrılan `collect_niche` fonksiyonu sayısı
- `successful`: fonksiyon hata fırlatmadan harita biçiminde döndü
- `failed`: beklenmeyen hata
- `quotaBlocked`: kota aşımı hatası alınmış sorgu
- `skipped`: kota zaten engellenmişken çağrılmayan sorgu
- `invalidResults`: başarılı görünen fakat sözleşmeye uymayan dönüş
- `videosFound`: arama sonuçlarında dönen toplam video kimliği
- `videosProcessed`: `videos_stored` alanı; yeni/benzersiz video sayısı **değil**
- `channelProfilesReported`: `channels_stored` alanı; yeni/benzersiz kanal **değil**

Sayılar bir sorgunun yeniden çalışmasında da artabilir. Kullanıcının arşivine
gerçekten yeni kaç kayıt eklendiği `db_stats` dönemler arası farkı veya özgün
kayıt logları ile ayrıca doğrulanmalıdır.

**Kapsam:** yalnız worker'ın `WORKER_QUERIES` listesi. Kullanıcının MCP ile
yaptığı manuel aramalar ve `watch_topic` günlük alarm aramaları bu özetin
dışındadır. Genel günlük kota sayacı bunları da kapsar. Worker hâlâ çalışıyor
mu sorusu için Docker sağlığı ayrıca kontrol edilir.

**Kota güvenliği:** Bir sorgu kota aşımı verdiğinde listedeki kalan sorgular
çağrılmadan `skipped` sayılır; ardışık hata veren isteklerle kotayı zorlamaz.

**Güvenlik:** meta kaydına sorgu metni, kanal ID'leri, ham API yanıtı, API
anahtarı veya istisna mesajı yazılmaz. Okuma tarafı JSON tiplerini ve aralıkları
doğrular; bozuk kayıtta `discoveryRun=null` döner. Çok kullanıcılı kurulumda
mevcut oturum doğrulama middleware'i korunur.

## Beş konu takibi ayrıca ölçülür

Worker'ın `watch_topic` yoluyla aradığı, kullanıcının seçtiği konular
`worker_topic_search_last_result` meta alanında ayrı tutulur. Yalnız
`topicsSearched`, `searchCalls`, `videosStored`, `stoppedBy`,
`skippedOwnerCount` ve ad/sır içermeyen çalışma durumu kaydedilir.

Bu yol eski video kimliklerini eleyerek yalnız yeni kimliklerle işlem
yaptığından `videosStored` farklı olarak **yeni video verisi işlemesini**
ifade eder. Bu sayı yine farklı bir zaman aralığındaki net veritabanı
artışı yerine kullanılamaz. Kota veya başarısızlık nedeniyle hiç arama
yapılmadıysa sıfır döner. Kullanıcının beş konu alarmı aktif olsa bile
Docker worker çalışmıyorsa sonuç kaydı oluşmaz.

## Yayına alma sınırı

Bu geliştirme `feat/brain-discovery-activity-v10` üzerine bir **Draft PR**
olarak hazırlanır. Testler, CI ve izole browser smoke başarıyla koşmadan
prod için onay verilmiş sayılmaz. Canlı ana dal, Nginx, Docker, PostgreSQL,
VDS timer'ları, MCP ve kota ayarları bu geliştirme sırasında değiştirilmez.

v9'daki `WORKER_QUERIES` konfigürasyonu sahada boşsa veri toplama başarılı
görünmez; `configuredTopics=0` görünür. v10/v11 ürün taslaklarını
birleştirmek, v9 canlı worker aktivasyonunun yerini tutmaz.
