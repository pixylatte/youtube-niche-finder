/* Editorial preparation is manual and ephemeral: no database write, no API quota.
 * The submitted source type and "reviewed" flag are USER assertions, NOT
 * verification by our service. Never send confidential notes here.
 */
import { api, esc, toast } from './ui.js';
import { requestProductionOutline } from './production-outline.js';

const SOURCE_TYPES = [
  ['archive', 'Arşiv / belge'],
  ['museum', 'Müze / koleksiyon'],
  ['academic', 'Akademik yayın'],
  ['official', 'Resmî kaynak'],
  ['quran', 'Kur’an / tefsir kaynağı'],
  ['hadith', 'Hadis kaynağı'],
  ['scholarly', 'İlmî açıklama'],
  ['other', 'Diğer'],
];
const BLOCKERS = {
  'original-angle-required': 'Rakip başlığından farklı, en az 30 karakterlik özgün anlatım açısı yazılmalı.',
  'two-independent-source-domains-required': 'En az iki farklı alan adından kaynak okunup işaretlenmeli.',
  'profile-specific-source-type-required': 'Kanalın türüne uygun kaynak seçilmeli.',
  'human-claim-review-required': 'Olgusal/dinî iddiaları insan tarafından inceleme adımı eksik.',
  'rights-and-licenses-review-required': 'Görsel ve ses materyallerinin hak/lisans değerlendirmesi eksik.',
  'production-effort-estimate-required': 'Üretim zorluğu belirlenmeli.',
};
const ID = /^[A-Za-z0-9_-]{11}$/;

function sourceRow(index) {
  return `<div class="form-row" style="gap:10px;flex-wrap:wrap;margin-top:8px">
    <label class="field"><span class="field-label">Bağımsız kaynak ${index + 1} (HTTPS)</span>
      <input class="bn-source-url" type="url" maxlength="500" style="min-width:250px"
        placeholder="https://ornek-kurum.org/belge"></label>
    <label class="field"><span class="field-label">Kaynak türü (senin beyanın)</span>
      <select class="bn-source-type">
        ${SOURCE_TYPES.map(([value, text]) => `<option value="${value}">${esc(text)}</option>`).join('')}
      </select></label>
    <label class="field" style="align-self:flex-end">
      <input type="checkbox" class="bn-source-reviewed"> Kaynağı bizzat okudum
    </label>
  </div>`;
}

function formFor(video, profile) {
  const name = profile === 'islam' ? '1 Dakika İslam' : 'Kayıp Sayfalar';
  return `<div class="card">
    <h2>Özgün Video Fikri — Editoryal Kontrol</h2>
    <p class="section-sub">Seçilen rakip referansı: ${esc(video.referenceTitle)}.
      Bu kayıt üretilecek videonun başlığı veya doğrulanmış bilgi kaynağı değildir.</p>
    <p class="section-sub">${esc(name)} için özgün bir soru/yorum geliştir;
      kaynağın doğruluğunu ve lisansını kendin incele. Bu form hiçbir bağlantıyı açıp
      doğrulamaz, veritabanına kaydetmez; sayfa yenilenince notlar kaybolur.</p>
    <form id="bnEditorialForm">
      <label class="field" for="bnAngle"><span class="field-label">Özgün anlatım açısı (en az 30 karakter)</span></label>
      <textarea id="bnAngle" rows="3" minlength="30" maxlength="1200" required
        style="width:100%;resize:vertical" placeholder="Rakip videoda cevapsız kalan soruyu veya yeni belgesel yaklaşımını tanımla."></textarea>
      ${[0,1,2].map(sourceRow).join('')}
      <div class="form-row" style="gap:14px;flex-wrap:wrap;margin-top:12px">
        <label class="field"><span class="field-label">Üretim zorluğu (kendi tahminin)</span>
          <select id="bnEffort">
            <option value="unknown">Henüz hesaplanmadı</option>
            <option value="low">Düşük — kaynak ve görseller elimde</option>
            <option value="medium">Orta — araştırma/kurgu gerekiyor</option>
            <option value="high">Yüksek — kapsamlı araştırma ve çekim gerekiyor</option>
          </select>
        </label>
      </div>
      <p><label><input type="checkbox" id="bnClaimsReviewed">
        İddiaları güvenilir bağımsız kaynaklarla kendim karşılaştırdım.</label></p>
      <p><label><input type="checkbox" id="bnRightsReviewed">
        Kullanacağım görsel, ses ve arşiv materyallerinin hak/lisans durumunu ayrıca kontrol ettim.</label></p>
      <button class="btn" id="bnReviewSubmit" type="submit">Editoryal eksikleri değerlendir</button>
    </form>
    <div id="bnEditorialOutcome" aria-live="polite"></div>
    <div id="bnProductionResult" aria-live="polite"></div>
  </div>`;
}

function reportHtml(result) {
  const ready = result.status === 'prepared-for-human-editorial-review';
  const list = (result.blockers || []).map(x => `<li>${esc(BLOCKERS[x] || x)}</li>`).join('');
  return `<div class="card" style="margin-top:10px">
    <h3>${ready ? 'İnsan editör incelemesine hazırlanmış' : 'Araştırma henüz tamamlanmadı'}</h3>
    <p class="section-sub">Bağımsız okunmuş kaynak alan adı: ${Number(result.uniqueReviewedSourceDomains) || 0}.
      Üretim zorluğu: ${esc(result.effortEstimate)}.</p>
    ${list ? '<ul>' + list + '</ul>' : '<p>Kontrol listesinde eksik alan görünmüyor.</p>'}
    <p class="section-sub"><strong>Bu bir yayın onayı değildir.</strong>
      Kaynak bağlantıları, tarihî/dinî iddialar ve materyal hakları sunucu tarafından
      doğrulanmadı. Tüm işaretlemeler kullanıcının beyanıdır.</p>
  </div>`;
}

function wireEditorialWorkbench(root, references, profile) {
  const panel = root.querySelector('#bnEditorialPanel');
  if (!panel || !Array.isArray(references)) return;
  const referencesById = new Map(references.filter(r => ID.test(r.videoId))
    .map(r => [r.videoId, r]));
  root.querySelectorAll('.bn-editorial-open').forEach(btn => {
    btn.addEventListener('click', () => {
      const video = referencesById.get(btn.dataset.videoId);
      if (!video) return;
      panel.innerHTML = formFor(video, profile);
      const form = panel.querySelector('#bnEditorialForm');
      const invalidate = () => {
        panel.querySelector('#bnEditorialOutcome').innerHTML = '';
        panel.querySelector('#bnProductionResult').innerHTML = '';
      };
      form.addEventListener('input', invalidate);
      form.addEventListener('change', invalidate);
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const sources = [...form.querySelectorAll('.bn-source-url')].flatMap(input => {
          const row = input.closest('.form-row');
          const url = input.value.trim();
          if (!url) return [];
          return [{
            url, type: row.querySelector('.bn-source-type').value,
            reviewed: row.querySelector('.bn-source-reviewed').checked,
          }];
        });
        const submit = panel.querySelector('#bnReviewSubmit');
        submit.disabled = true;
        try {
          const payload = {
            profile, referenceTitle: video.referenceTitle,
            angle: panel.querySelector('#bnAngle').value,
            sources, effort: panel.querySelector('#bnEffort').value,
            claimsReviewed: panel.querySelector('#bnClaimsReviewed').checked,
            rightsReviewed: panel.querySelector('#bnRightsReviewed').checked,
          };
          const result = await api('/api/editorial/readiness', {
            method: 'POST', body: payload,
          });
          if (!form.isConnected) return;
          const outcome = panel.querySelector('#bnEditorialOutcome');
          outcome.innerHTML = reportHtml(result)
            + '<button class="btn btn-ghost" type="button" id="bnProductionRequest">'
            + 'Seslendirme ve sahne üretim taslağını oluştur</button>';
          outcome.querySelector('#bnProductionRequest').addEventListener('click',
            () => requestProductionOutline(panel, payload));
        } catch (e) {
          toast(e.message, 'err');
        } finally {
          submit.disabled = false;
        }
      });
    });
  });
}

export { wireEditorialWorkbench };
