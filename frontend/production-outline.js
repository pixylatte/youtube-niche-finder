/* Display a provisional source-first production outline. Never auto-publish,
 * generate unsupported claims, create audio, or fetch YouTube data.
 */
import { api, esc, toast } from './ui.js';

const STEP_NAMES = {
  hook: 'Giriş / izleyici sorusu',
  context: 'Konu ve bağlam',
  evidence: 'Doğrulanacak temel kanıt',
  comparison: 'Kaynakların karşılaştırılması',
  assessment: 'Sınırlamalar ve yorumlar',
  lesson: 'Dikkatli çıkarım',
  closing: 'Sonuç ve kaynak yönlendirmesi',
};
const VISUAL_NAMES = {
  'document-detail': 'Belge detayı',
  'animated-map': 'Animasyonlu harita',
  'archive-document': 'Arşiv belgesi',
  'timeline-comparison': 'Zaman çizelgesi',
  'minimal-explainer': 'Açıklayıcı animasyon',
  'source-list': 'Kaynak listesi',
  'typography-hook': 'Yazı animasyonu',
  'subtle-context-motion': 'Hafif hareketli açıklama',
  'source-text-card': 'Kaynak metin kartı',
  'animated-explainer': 'Anlatım animasyonu',
  'source-end-card': 'Kaynak bitiş kartı',
};
const BLOCKERS = {
  'original-angle-required': 'Özgün anlatım açısı eksik veya referans başlığına çok benziyor.',
  'two-independent-source-domains-required': 'İki farklı kaynak alan adı incelemesi eksik.',
  'profile-specific-source-type-required': 'Kanalın bilgi türüne uygun kaynak sınıfı eksik.',
  'human-claim-review-required': 'İddiaların insan tarafından doğrulama beyanı eksik.',
  'rights-and-licenses-review-required': 'Görsel/ses hak ve lisans kontrolü eksik.',
  'production-effort-estimate-required': 'Üretim iş yükü tahmini eksik.',
};

function productionPlanHtml(plan) {
  const fmt = plan.format || {};
  const ratio = esc(fmt.aspectRatio || '—');
  const form = plan.profile === 'islam' ? '1 Dakika İslam / Shorts' : 'Kayıp Sayfalar / belgesel';
  const blockers = (plan.researchBlockers || []).map(key =>
    `<li>${esc(BLOCKERS[key] || key)}</li>`).join('');
  const scenes = (plan.scenes || []).map((scene, index) => `<div class="card" style="margin-top:8px">
    <div style="display:flex;gap:8px;justify-content:space-between;flex-wrap:wrap">
      <strong>${index + 1}. ${esc(STEP_NAMES[scene.id] || scene.id)}</strong>
      <span class="section-sub">${Number(scene.startSeconds)}–${Number(scene.endSeconds)} sn</span>
    </div>
    <p>${esc(scene.purpose)}</p>
    <p class="section-sub"><strong>Seslendirme:</strong> ${esc(scene.narrationInstruction)}</p>
    <p class="section-sub"><strong>Görsel/Remotion:</strong>
      ${esc(VISUAL_NAMES[scene.visualTreatment] || scene.visualTreatment)}</p>
    <p class="section-sub"><strong>Kontrol:</strong> ${esc(scene.sourceAndRightsCheck)}</p>
  </div>`).join('');
  const voiceSteps = (plan.voiceover?.workflow || []).map(step => `<li>${esc(step)}</li>`).join('');
  const status = plan.planStatus === 'outline-for-human-review'
    ? 'İnsan incelemesine sunulabilecek taslak' : 'Eksik araştırmalarla birlikte geçici taslak';
  return `<div class="card">
    <h2>Video Üretim Taslağı — v14</h2>
    <p class="section-sub"><strong>${esc(form)}</strong> ·
      ${ratio} · ${Number(fmt.width)}×${Number(fmt.height)} ·
      ${Number(fmt.fps)} FPS · örnek ${Number(fmt.targetSeconds)} sn</p>
    <p><strong>Durum:</strong> ${esc(status)}</p>
    <p class="section-sub"><strong>Özgün fikir açısı (henüz doğrulanmadı):</strong>
      ${esc(plan.workingAngle)}</p>
    ${blockers ? `<p><strong>Üretimden önce eksikler:</strong></p><ul>${blockers}</ul>`
      : '<p>Form eksikleri giderilmiş; yine de gerçek kaynak ve yayın doğrulaması gerekiyor.</p>'}
    <p class="section-sub">Bu bir senaryo metni, doğrulanmış kaynak listesi, üretilmiş animasyon
      veya yayın onayı değildir. Sahne süreleri gerçek seslendirmeye göre değiştirilecektir.</p>
  </div>
  <div class="card">
    <h3>Kendi sesinle kayıt ve kurgu akışı</h3>
    <ol>${voiceSteps}</ol>
    <p class="section-sub">Ses dosyası oluşturulmadı; WAV kayıt ve temizleme insan tarafından yapılmalı.</p>
  </div>
  <div class="card">
    <h3>Sahne storyboard iskeleti</h3>
    <p class="section-sub">Sahne metinleri ve görseller gerçek kaynaklar doğrulanınca hazırlanacaktır.</p>
  </div>
  ${scenes}
  <div class="card">
    <h3>Son kontrol</h3>
    <ul>
      ${(plan.checklist || []).map(item => `<li>${esc(item.why)} — tamamlanmadı</li>`).join('')}
    </ul>
    <p><strong>Yayın onayı:</strong> Yok · <strong>YouTube API kullanımı:</strong> 0 ·
      <strong>AI senaryo üretimi:</strong> Yok</p>
  </div>`;
}

async function requestProductionOutline(panel, payload) {
  const button = panel.querySelector('#bnProductionRequest');
  const target = panel.querySelector('#bnProductionResult');
  if (!button || !target) return;
  button.disabled = true;
  button.textContent = 'Taslak hazırlanıyor…';
  try {
    const result = await api('/api/editorial/production-plan', { method: 'POST', body: payload });
    if (!button.isConnected || !target.isConnected) return;
    target.innerHTML = productionPlanHtml(result)
      + '<button type="button" class="btn btn-ghost" id="bnCopyProductionJson">'
      + 'Remotion/Codex için plan JSON’unu kopyala</button>';
    target.querySelector('#bnCopyProductionJson').addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
        toast('Üretim planı JSON olarak panoya kopyalandı.');
      } catch (e) {
        toast('Panoya kopyalama kullanılamadı. Güvenli HTTPS bağlantısı gerekebilir.', 'err');
      }
    });
    target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (error) {
    toast(error.message, 'err');
  } finally {
    if (button.isConnected) {
      button.disabled = false;
      button.textContent = 'Seslendirme ve sahne üretim taslağını oluştur';
    }
  }
}

export { requestProductionOutline, productionPlanHtml };
