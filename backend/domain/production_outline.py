"""Conservative, local-only production outlines from a human editorial review.

The output is an editable *structure*, not a fact-checked script. It never
invents historical facts, Quran quotations, hadith texts, citations, copyright
licenses or guaranteed production costs. No YouTube/LLM calls or persistence.
"""
from domain import editorial_readiness as ER

WORKFLOWS = {
    "kayip": {
        "workingFormat": "historical-documentary",
        "canvas": {"width": 1920, "height": 1080, "aspectRatio": "16:9",
                   "fps": 30, "targetSeconds": 420},
        "steps": [
            ("hook", 0, 20, "Belgelenmiş bir soruyla aç; doğrulanmamış bir iddiayı gerçek gibi sunma.",
             "Rakip başlığını kopyalamadan kendi araştırma sorunu seslendir.",
             "document-detail", "Ekranda gösterilecek belgenin kaynağı ve kullanım izni ayrı incelenmeli."),
            ("context", 20, 90, "Dönemin tarihî bağlamını ve olayın geçtiği yeri açıklamaya hazırlan.",
             "Bağlam metnini birincil ve akademik kaynakları inceledikten sonra yaz.",
             "animated-map", "Haritadaki sınırları, tarihleri ve yer adlarını doğrula."),
            ("evidence", 90, 210, "Birincil kaynakların gerçekten hangi bilgileri desteklediğini göster.",
             "Doğrulanmış kanıtları seslendir; belirsiz noktaları açıkça ayır.",
             "archive-document", "Arşiv belgesi görsellerinin telif ve yeniden kullanım koşullarını kontrol et."),
            ("comparison", 210, 310, "Farklı yorumları karşılaştır; gerçekte olmayan görüş ayrılıkları üretme.",
             "Doğrudan belge bilgisini kendi yorumundan net biçimde ayır.",
             "timeline-comparison", "Zaman çizelgesindeki tarihleri, görselleri ve kaynak atıflarını doğrula."),
            ("assessment", 310, 385, "Kaynakların sınırlarını ve mevcutsa alternatif açıklamaları tartış.",
             "Kaynakların sustuğu veya birbirinden ayrıldığı noktaları belirt.",
             "minimal-explainer", "Kişi, alıntı veya arşiv görüntüsü uydurma."),
            ("closing", 385, 420, "Bilinenleri ve cevaplanmamış soruları birlikte toparla.",
             "Yalnızca kontrol edilmiş noktaları özetleyerek bitir.",
             "source-list", "Yayından önce gerçekten kullanılan kaynakların bağlantılarını ekle."),
        ],
        "sourceCategories": ["archive", "museum", "academic", "official"],
        "visualStrategy": "Önce uygun lisanslı gerçek arşiv materyalleri; harita, etiket ve kronoloji için Remotion kullan.",
    },
    "islam": {
        "workingFormat": "islamic-educational-short",
        "canvas": {"width": 1080, "height": 1920, "aspectRatio": "9:16",
                   "fps": 30, "targetSeconds": 60},
        "steps": [
            ("hook", 0, 4, "Kısa ve açık bir soruyla başla; dinî sansasyon iddiasından kaçın.",
             "Shorts'a uygun tek bir özgün soru seslendir.",
             "typography-hook", "Kaynağı bilinmeyen sözleri dinî alıntı olarak aktarma."),
            ("context", 4, 15, "Konunun ne olduğunu kısa ve anlaşılır biçimde anlatmaya hazırlan.",
             "Kavramı varsayımla değil, incelenmiş dinî kaynakla açıkla.",
             "subtle-context-motion", "Uydurma kutsal metin veya yanıltıcı görsel kullanma."),
            ("evidence", 15, 38, "İncelenmiş bir ayet, hadis veya ilmî açıklamaya odaklan.",
             "Metnin asıl ifadesini ancak referans ve yorum incelemesinden sonra yaz.",
             "source-text-card", "Kaynak numarasını, metni, tercümeyi ve kullanım koşullarını kontrol et."),
            ("lesson", 38, 53, "Kaynağın desteklediği ölçüde dikkatli bir çıkarım yap.",
             "Kaynak ifadesini kendi açıklamandan açıkça ayır.",
             "animated-explainer", "Yanıltıcı canlandırmalardan ve temelsiz kesin hükümlerden kaçın."),
            ("closing", 53, 60, "Kaynağın bağlamını hatırlatarak kısa bitir.",
             "Uydurma vaatler veya dayanağı olmayan dinî hükümler ekleme.",
             "source-end-card", "Kaynak kartını yalnız bağımsız inceleme sonrasında göster."),
        ],
        "sourceCategories": ["quran", "hadith", "scholarly"],
        "visualStrategy": "Net altyazı animasyonları ve lisanslı görseller kullan; dinî alıntı uydurma.",
    },
}


def build(payload):
    """Build a bounded plan using the *same* validation as editorial readiness."""
    review = ER.evaluate(payload)
    profile = review["profile"]
    template = WORKFLOWS[profile]
    angle = payload.get("angle", "").strip()
    # The user's own text is marked as an unverified working angle. Reuse is
    # limited to the 1,200 characters already checked by ER.evaluate.
    scenes = [
        {"id": key, "startSeconds": start, "endSeconds": end,
         "purpose": purpose, "narrationInstruction": narration,
         "visualTreatment": treatment, "sourceAndRightsCheck": safeguard,
         "scriptText": None, "assetsAttached": False, "claimsVerified": False}
        for key, start, end, purpose, narration, treatment, safeguard
        in template["steps"]
    ]
    return {
        "profile": profile,
        "workingFormat": template["workingFormat"],
        "workingAngle": angle,
        "angleVerification": "user-supplied-not-fact-checked",
        "format": template["canvas"],
        "scenes": scenes,
        "sourceCategoriesToReview": template["sourceCategories"],
        "submittedSourceCount": review["submittedSources"],
        "reviewedSourceDomainCount": review["uniqueReviewedSourceDomains"],
        "sourceLinksVerified": False,
        "researchBlockers": review["blockers"],
        "researchStatus": review["status"],
        "planStatus": ("outline-for-human-review" if not review["blockers"]
                       else "blocked-provisional-outline"),
        "productionEffort": {
            "userEstimate": review["effortEstimate"],
            "monetaryCostKnown": False,
            "costEstimate": None,
        },
        "voiceover": {
            "method": "creator-recorded-external-microphone",
            "language": "tr",
            "workflow": [
                "Kendi sesini harici mikrofonla sessiz bir ortamda kaydet.",
                "Kayıpsız WAV ana kayıt sakla; seviyeleri ve patlamaları kontrol et.",
                "Gürültüyü temizle, hataları kes ve konuşma anlaşılırlığını dengeli hâle getir.",
                "Render öncesi sahne sürelerini onaylanan gerçek ses kaydıyla eşleştir.",
            ],
            "recorded": False,
            "durationVerified": False,
        },
        "visuals": {
            "strategy": template["visualStrategy"],
            "animationTool": "Remotion",
            "assetLicensesVerified": False,
            "sourceProvenanceVerified": False,
            "rendered": False,
        },
        "checklist": [
            {"id": "claims", "done": False, "why": "Tarihî ve dinî ifadeleri bağımsız güvenilir kaynaklarla tek tek doğrula."},
            {"id": "sources", "done": False, "why": "Gerçek kaynak belgelerini, sayfaları ve atıfları incele."},
            {"id": "rights", "done": False, "why": "Her görselin, videonun ve sesin lisansını ve izinlerini kontrol et."},
            {"id": "voice", "done": False, "why": "Kendi seslendirmeyi kaydet ve baştan sona dinleyerek incele."},
            {"id": "timing", "done": False, "why": "Sahne sürelerini ölçülmüş seslendirme süresine göre yeniden ayarla."},
            {"id": "originality", "done": False, "why": "Yeni anlatının rakiplerin içeriğini taklit etmediğini kontrol et."},
            {"id": "final-review", "done": False, "why": "Yayından önce son insan editör kontrolünü tamamla."},
        ],
        "autoGeneratedScript": False,
        "publicationApproved": False,
        "youtubeQuotaUsed": 0,
        "llmUsed": False,
        "databaseWritten": False,
        "note": ("Bu yalnızca geçici bir iskelettir. Kaynaklar, olgular, haklar, süreler, metin "
                 "ve tamamlanmış sahneler bağımsız olarak doğrulanmamıştır."),
    }
