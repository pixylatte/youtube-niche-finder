# YouTube Brain → YouTube Brain Next: özellik envanteri ve seçici aktarım
## 28 Ekim 2026 — esas hedef: `pixylatte/youtube-niche-finder`

**Karar:** Eski `pixylatte/youtube-brain` (Next.js/Supabase + VDS) çalışmaya
devam eder. Yeni YouTube Brain Next, `pixylatte/youtube-niche-finder`
(Python/FastAPI/PostgreSQL + MCP) üzerinde **ayrı ürün** olarak gelişir.
Veritabanı, hesap/OAuth ve çalıştırma ortamları birleştirilmez; prod dağıtımı
bu geliştirmeyle yapılmaz. Yeni araştırma/değerlendirme özelliklerinin kod
hedefi yalnız yeni depodur.

## Kod envanteri — hangisini taşıyoruz?

| Eski YouTube Brain parçası | Yeni sistemdeki mevcut karşılığı | Karar |
|---|---|---|
| `competitor-discovery.ts` / rakip arama | `collecting.py`, `discovery.py`, `topic_watch.py`, `worker_cycle.py`; seçilebilir Shorts/uzun format | **Kopyalama:** yeni sistem zaten video uzunluğunu filtreleyebiliyor; eski PR #112'nin TypeScript arama kodu doğrudan kullanılmaz |
| `niche-opportunities.ts` / trend ve rakip puanlama | `domain/niche_ranking.py`, `application/saturation.py`, `application/niche_clusters.py` | **Karşılaştır:** mevcut matematik ve sınırlamaları koru; aynı puanlayıcıyı ikinci kez yazma |
| `opportunity-evidence-quality.ts` / bağımsız rakip, yayın ve tarama güncelliği | `search.niche_overview()` arşiv metrikleri var ama açık bir örnek kalitesi kapısı yok | **Aktarıldı (bu PR):** `domain/archive_evidence.py` + niş API + panel; mevcut satırları kullanır, 0 kota |
| `channel-dna.ts` / kendi kanalının 24 saatlik gerçek videolarından karşılaştırma | `own_channels.py` OAuth Analytics, `trajectory.py` ve `video_stats_history` | **Sonraya bırak:** 24h checkpoint kanıtı ile günlük Analytics sayıları eşdeğer değildir; kesin ölçüm olmadan uygulanamaz |
| `post-publish-learning-readiness.ts` ve 1h/6h/24h/72h ölçüm pencereleri | Worker yaklaşık üç saatte bir örnek alır, `trajectory.py` zaten var | **Bu toplu dalda uyarlanıyor:** kesin 1h/24h checkpoint yerine yalnız ölçülmüş ilk-gün aralıkları ve veri kalitesi |
| Eski Supabase kota tabloları, eski F0 eşzamanlı kota PR'ları | Yeni PostgreSQL API sayaçları, 3.000 birim ve 100 search çağrısı; worker ve MCP kullanımı | **SQL/kodu kopyalama:** farklı şema ve reset kuralları; ayrı kota bütünlüğü/integrasyon testleri planla |
| Eski VDS systemd/PM2/Nginx, onay imzası ve cutover scriptleri | Yeni Docker Compose worker ve uygulama; kendi MCP bağlantısı | **Taşıma:** VDS operasyon aracı başka bir sistemin anahtarı ve ayrı güvenlik sınırıdır |
| Eski fikir/senaryo/ses/Remotion içerik üretim katmanları | Yeni ürünün araştırma hedefi dışında | **Taşıma:** kullanıcı yalnız YouTube Brain sisteminin araştırma/analiz/ajan tarafını geliştiriyor |
| Eski `owner-evidence-decision.ts` / kendi 24h verisi ile ihtiyatlı karar | Yeni `own_formats.py` / `own_metrics.py`, niş araştırmaları | **Değerlendir:** ancak güvenilir karşılaştırılabilir gözlem sayısı ve aynı format tespit edildiğinde önerilen kararların açıklanmasında kullan |
| Eski GitHub Actions sistem testleri | Yeni depoda bağımsız Ruff/pytest/Chromium/Postgres CI | **Kavramı koru:** test sürecini kullan, pipeline/bağımlılıkları rastgele kopyalama |

## Bu aktarımın gerçek sınırı

`backend/domain/archive_evidence.py`, eski sistemin kaynak-kanıtı yaklaşımını
yeni sisteme **yeniden kodlar**, eski Supabase örneklerini arşive taşımaz.
Şu veriler ayrıdır:

- Benzersiz video ve kanal sayısı (aynı video tekrarlarını saymaz).
- Son 45 günde yayınlanmış video sayısı ve en az 2× outlier örnek sayısı.
- En son video **yayın tarihi** ile en son niş **toplama tarihi** ayrı ayrı.
- Örnek kalitesi: `supported-sample`, `limited`, `no-signal` veya `unavailable`.
- Boş/eksik tarih veya tek kanal "kesin fırsat" sayılmaz.
- `supported-sample`, nişte minimum arşiv örneği bulunduğu anlamına gelir:
  bütün rakiplerin eksiksiz tarandığı, YouTube çapında talep doğrulandığı,
  kaynağın doğru olduğu veya gelecekte video başarılı olacak demek değildir.

Mevcut `GET /api/niches/{slug}` yanıtına yalnız `evidenceQuality` eklenir.
Ek HTTP endpoint, DB migration, YouTube/LLM isteği, worker tetikleme veya
kota harcaması yoktur. Mevcut skorları, sıralamaları ve niş seçimlerini
değiştirmez. Aynı veriyi kullanan niş ekranında kanıt bilgisi görüntülenir.

## Geliştirme sırası

1. Bu PR: niş örnek kalitesi + regression tests + mevcut ekranda gösterim.
2. Yeni sistemin **v9–v11 discovery aktivasyon taslaklarını**, ayrı basılmış
   video üretim taslaklarına bağlı olmadan CI/worker doğrulamasından geçir.
   `WORKER_QUERIES` ve kayıtlı `watch_topic` kendi başlarına canlı worker
   sağlığının kanıtı değildir.
3. Kota eşzamanlılık ve çok kullanıcı ayrımını, yeni PostgreSQL modeli
   içinde ayrı ve atomik test et. Eski F0 Supabase migration'larını kullanma.
4. Sonradan gerçekten ölçülmüş sahip kanal ve rakip verileriyle
   yayın sonrası öğrenme / 24h kıyasını **ortak format** bazında tasarla.
5. Yeni ajan/karar merkezini, mevcut MCP/worker görevlerinin kanıtlı
   arşiv çıktıları üzerinden geliştir; üretim motoru ekleme.

## Yayın güvenliği

Eski GitHub PR #112, **eski sistemin** kodudur. Yeni sisteme geçirilmiş
sayılmaz. Yeni sistemdeki #11–#16 taslakları da birleşmiş/canlı değildir.
Bu PR, yeni `main` üzerine bağımsız hazırlanır. Test sonucu ve yayın
onayı oluşmadan yalnız kaynak kodu değişmiş sayılır. Eski YouTube Brain
servisi, yeni Niche Finder Docker worker, Nginx, API anahtarları, otomasyon
görevleri ve PostgreSQL canlı verisi değiştirilmez.
