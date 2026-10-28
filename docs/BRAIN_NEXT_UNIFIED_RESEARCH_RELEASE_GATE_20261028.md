# YouTube Brain Next — Araştırma Sistemi Toplu Entegrasyon

**Tarih:** 28 Ekim 2026  
**GitHub ana depo:** `pixylatte/youtube-niche-finder`  
**Kaynak dallar:** v2–v12 birikimli hat, rakip formatı #9 ve eski Brain kanıt modülü #17  
**Bilinçli dış kapsam:** v13 ve v14 video/seslendirme/animasyon üretimi

## Aktarılan ve birlikte korunmuş özellikler

| Kategori | Mevcut çalışan çekirdek / taşınan özellik | Durum |
|---|---|---|
| Türkçe YouTube Brain arayüzü | v2–v3 UI, TR/EN/RU sözlükler, gruplanmış menü, tarayıcı testleri | Toplu dalın temelinde |
| Arşiv veri kapsamı | video, kanal, snapshot, vektör sayıları; yetersiz veri uyarıları | Toplu dalın temelinde |
| Niş karşılaştırması | kanıt, çoklu sinyal, arşiv sınırlılıkları | Toplu dalın temelinde |
| Rakip kanal | ayrı kanal kanıt paneli, 2–3 kanalı karşılaştırma | Toplu dalın temelinde |
| Rakip formatlarının tekrarlanması | kayıtlı uzun videodan başka kanalların benzer video performansını **isteğe bağlı** inceleme | Bu dalda yeniden bağlandı |
| Otonom keşif teşhisi | worker işaretleri, günlük kota, watch_topic sonuçları; başarı iddiası için gerçek olay verisi | v9–v11 temelinde |
| Günlük araştırma referansları | iki editoryal kanal profili için ayrı, yerel veri tabanlı, uydurma önerisiz değerlendirme | v12 temelinde |
| Eski Brain'den fırsat **kanıtı kalitesi** | benzersiz video/kanal, son 45 gün yayınları, >=2× outlier, ayrı arşiv toplama tazeliği | Bu dalda Python'a taşındı |
| Eski sistemdeki ortak kota güvenliği | Niche Finder'ın kendi PostgreSQL atomik `_reserve` ve `test_quota_concurrency.py` vardır | Tekrar kopyalanmadı; mevcut kod/test korunur |
| Eski yayın sonrası hız ve istatistik | Yeni sistemde `trajectory.py`, `video_stats_history`, `own_channels.py` OAuth Analytics ve otomatik istatistikler vardır | Tekrar yazılmadı, doğrudan aktarılmadı |
| Eski VDS kontrol ve özel imza araçları | Farklı makine, farklı kimlik ve mimari; Niche Finder Docker hizmeti | **Taşınmadı**: güvenlik sınırı |
| Yeni sistemin v13–v14 üretim motoru | kullanıcının araştırma sistemi hedefinin dışında | **Taşınmadı** |

## Rakip formatı aktarımının sınırları

Mevcut `GET /api/channels/{id}` zaten yalnız **uzun videolardan**
`topOutliers` hesaplar. Yalnızca kullanıcının `#/channel-compare/...`
ekranındaki düğmeye basmasıyla en fazla üç yerel
`GET /api/videos/{id}/repeatability` sorgusu başlatılır. Yeni YouTube
`search.list`, LLM veya dış API harcaması yapılmaz.

Bulgular, başka kanalların benzer içeriklerle arşivlenen performansına
dayanır; **YouTube genelinin rekabet sonucu, garantili başarılı format veya
özgün konu değildir.** Geçersiz video ID'leri bağlantıya dönüştürülmez;
eksik veriler başarı diye yorumlanmaz.

## Kanıt kalitesi

Eski Brain'deki `opportunity-evidence-quality.ts` yaklaşımı doğrudan
TypeScript/Supabase koduyla değil, yeni Python domain sınırlamasıyla taşındı.
Var olan `GET /api/niches/{slug}` yanıtı `evidenceQuality` alanını
kazandı; nicel niş sıralaması ve başarı skorları **değişmez**. UI
TR/EN/RU destekler. Son arşiv toplama işareti bütün rakiplerin güncel
ölçümünü kanıtlamaz.

## Canlıya alma kapısı (henüz açılmadı)

1. **Kod**: GitHub dalları üzerinden yeni tek toplu PR; eski `main` ve VDS
   aynı kalır. Birikimli v2–v12 gelişimi ile çapraz PR #17 / rakip formatı
   birleşimi tek PR'da incelemeye hazır hâle gelir.
2. **CI**: Ruff, API doküman kontrolü, link denetimi, PostgreSQL testleri,
   üç dilde Chromium smoke ve yeni iki entegrasyon testi gerçek ortamda PASS.
   **CI başlamadıysa/sonuç yoksa PASS iddiası yapılmaz.**
3. **Veri**: gerçek kanallarda performans veri kapsaması ve yeterli örnek
   doğrulanır; yerel arşiv geçici nişler için uydurma güven sağlamaz.
4. **Canlı öncesi**: Docker Compose ortam değişkenleri, DB yedeği,
   rollback, worker lock, API anahtarı ve kota izolasyonu incelemesi.
5. **Yayın**: operatör onayı alındığında tek kontrollü deploy.
   Bu belge deploy komutu çalıştırmaz.

## Gerçek tamamlanma kriteri

Bir özelliğin PR'da olması **canlıya aktarıldığı** anlamına gelmez.
Eski `pixylatte/youtube-brain` GitHub kodunu ve eski VPS zamanlayıcılarını
değiştirmiyoruz. Eski sistemi kapatmak için kanıt veya talimat henüz yok.
Video, ses, Remotion, render ve video senaryosu geliştirmesi bu entegrasyonun
parçası değildir.
