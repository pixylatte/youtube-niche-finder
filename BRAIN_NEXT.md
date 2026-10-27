# YouTube Brain Next — ürün odaklı geliştirme

Bu depo, [pandich93/youtube-niche-finder](https://github.com/pandich93/youtube-niche-finder) MIT lisanslı projesinin fork'udur. Orijinal `LICENSE` korunur. Astra / `pixylatte/youtube-brain` ayrı üründür ve değiştirilmeyecektir.

## v0.1 — Günlük Video Karar Merkezi

Erişim: web paneli menüsünden **Günlük Video Karar Merkezi** veya `#/brainNext`.

- İki bağımsız **çalışma profili**: Kayıp Sayfalar ve 1 Dakika İslam. Bu yalnız konu ve taslak ayrımıdır; gerçek kanal hesabı, OAuth veya analytics bağlantısı değildir.
- Örnek konu listeleri yalnız **araştırma başlangıcıdır**. Bir konu seçimi, video tavsiyesi veya trend kanıtı sayılmaz.
- Kullanıcı bir satıra bir konu yazar, en fazla 12 benzersiz fikri tek çağrıda mevcut `POST /api/ideas/check` yoluyla kontrol eder.
- Yanıt sadece zaten toplanmış **yerel video arşivi** ile ilgilidir; yeni YouTube araması, ücretli LLM veya harici veri toplama yapılmaz.
- `verdict=proven` ve `matchCount>0` olan en fazla 3 fikir, kaynak video bağlantılarıyla *kanıtlı araştırma adayı* olur. `recent` / `free` / `flopped` sonuçları kesin öneri olarak sunulmaz. Ölçülen outlier'lar YouTube garantisi değil, corpus istatistiğidir.
- Var olan Niche açılır filtresi sonuçlarda korunur ve belirtilir; kanal başlığı kendi başına arama veya niş filtresi uygulamaz.
- Taslaklar ve profil seçimi uygulamanın tarayıcı oturumunda/lokal ayarlarında tutulur; şimdilik çok cihazlı senkronizasyon veya gerçek kanala yazma yok.
- API hata verirse kullanıcıya gösterilir; sonuçlar sıfırsa açıkça *kanıt yetersiz* denir.

## v0.1 tamamlandı kabul koşulları

- [ ] Headless Chromium smoke testi yeni `brainNext` sayfasını **İngilizce/Rusça kabuklarda** hatasız açar.
- [ ] Kontrollü POST örnekleriyle kanıtlı, kanıtsız ve kanal değiştirme senaryoları geçer; dış YouTube API kotası harcanmaz.
- [ ] `main` değiştirilmeden draft PR incelenir, testleri geçer; sonra ayrıca güvenli dağıtım onayı alınır.
- [ ] Çalışan Niche Finder ve Astra/VDS diğer konteynerleriyle çakışmayan ayrı staging/backup doğrulanır.
- [ ] Canlı veri yeterli değilse ekran *yetersiz kanıt* döndürür; bilinmeyenleri puanlamaz.

## Sonraki görünür ürün adımları

1. Saha verisi ve kanal bağlantıları doğrulandıktan sonra gerçek kanal/niş bazlı keşif.
2. Türkçe dil paketi (mevcut ru/en altyapısını bozmadan; sadece yeni ekranın Türkçe olması tüm ürünün yerelleştirildiği anlamına gelmez).
3. Kaynaklı günlük kısa rapor, içerik brief'i ve yayın planı.
4. Güvenli HTTPS/MCP üzerinden doğrudan ChatGPT araştırma akışı.

## Dağıtım güvenliği

Mevcut kuruluma ait önceki VDS notları: `89.47.113.16` üzerinde `/opt/youtube-niche-finder`. Bu bilgi son kullanıcı tarafından bildirilen/geçmiş oturumda gözlemlenen konumdur, **canlı bağlantı testi değil**. Bu PR **yalnız GitHub taslağıdır**; staging kurulumu, Docker restart, migration veya deploy yapılmadı. Yeni araçlar için ayrı VDS yönetim bağlantısı ve uygun yürütme/onay gerekir. Çalışan konteyner, veritabanı ve `.env` korunur.
