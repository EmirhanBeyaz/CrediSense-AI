# CrediSense AI Yol Haritası

Bu dosya, projenin hangi sırayla geliştirileceğini anlatır. Amaç sadece yapılacakları
listelemek değil, projeye yeni gelen birinin neden o adımın gerekli olduğunu anlamasını
sağlamaktır.

## Mevcut Durum

CrediSense AI şu anda terminalden çalışan bir prototiptir. Örnek sentetik PDF belgelerini
okuyabilir, alanları çıkarabilir, tutarlılık kontrolü yapabilir ve baseline risk skoru
üretebilir.

Şu anda hazır olanlar:

- [x] Katmanlı Python backend akışı
- [x] Örnek sentetik PDF belgeleri
- [x] Örnek başvuru formu
- [x] JSON ve Markdown rapor üretimi
- [x] Test altyapısı
- [x] GitHub Actions CI taslağı
- [x] Kurulum ve çalıştırma anlatımı
- [x] FastAPI ile temel HTTP API

Şu anda eksik olan ana parçalar:

- [ ] Gerçek belge dayanıklılığı
- [ ] API servisi
- [ ] Web arayüzü
- [ ] Üretime uygun model/veri yönetimi
- [ ] Güvenlik, kişisel veri ve audit kayıtları

## Faz 1: Kurulum ve Kalite Temeli

Bu fazın amacı projeyi herkesin aynı şekilde kurup test edebilmesini sağlamaktır.

Tamamlanan işler:

- [x] `pyproject.toml` eklendi.
- [x] `pytest` test altyapısı eklendi.
- [x] Örnek PDF'lerle uçtan uca analiz testi eklendi.
- [x] Başvuru formu okuma davranışı test altına alındı.
- [x] CLI eksik PDF ve hatalı form dosyalarında anlaşılır hata verir.
- [x] README daha açık kurulum adımlarıyla güncellendi.

Bu fazdan sonra yeni bir geliştirici şu komutlarla projeyi kontrol edebilmelidir:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
```

Beklenen sonuç:

```text
7 passed
```

## Faz 2: Belge Okuma ve Alan Çıkarma

Bu fazın amacı sistemin sadece sentetik örneklerle değil, daha farklı PDF formatlarıyla da
çalışabilmesini sağlamaktır.

Tamamlanan işler:

- [x] `katman_01_pdf_okuma.py` içine `PyMuPDF` tabanlı birincil okuyucu eklendi.
- [x] Mevcut özel PDF okuyucu fallback olarak korundu.
- [x] PDF okuma sonucuna `extractor` ve `warnings` alanları eklendi.
- [x] Katman 01 için temel testler eklendi.
- [x] Analiz çıktısına `document_quality` özeti eklendi.
- [x] Belge anlama sonucuna `missing_fields` ve `warnings` eklendi.
- [x] Markdown rapora `Belge Okuma Kalitesi` bölümü eklendi.

Sıradaki işler:

- [ ] Taranmış belgeler için OCR opsiyonunu araştır ve küçük bir deneme ekle.
- [ ] Belge okuma sonucuna güven skoru ekle.
- [ ] Farklı PDF örnekleriyle test dosyaları ekle.

Başarı ölçütü:

- Örnek belgeler bozulmadan çalışmalı.
- Metin çıkarılamayan PDF için sistem sessizce yanlış karar üretmemeli.
- Kullanıcı raporda hangi belgenin neden sorunlu olduğunu görebilmeli.

## Faz 3: API Servisi

Bu fazın amacı terminal komutunu bir backend servisine çevirmektir.

Tamamlanan işler:

- [x] FastAPI bağımlılığı eklendi.
- [x] `backend/credisense/api.py` dosyası oluşturuldu.
- [x] Sağlık kontrolü için `GET /health` endpoint'i eklendi.
- [x] Analiz için `POST /analyze` endpoint'i eklendi.
- [x] Kimlik, bordro, banka PDF'i ve başvuru formu yüklenebilir hale geldi.
- [x] Endpoint çıktısı mevcut terminal JSON sözleşmesiyle uyumlu tutuldu.
- [x] API için testler eklendi.
- [x] Analiz cevabına `analysis_id` eklendi.
- [x] API hata cevapları standart gövdeye bağlandı.
- [x] `GET /reports/{analysis_id}/{report_type}` endpoint'i eklendi.

Sıradaki iyileştirmeler:

- [ ] Dosya boyutu limiti ekle.
- [ ] API validasyon hatalarını da aynı hata şemasına çevir.
- [ ] Rapor üretimini ileride veritabanı veya nesne depolama arkasına taşı.
- [ ] Analiz ID'sini uzman inceleme akışıyla ilişkilendir.

Başarı ölçütü:

```powershell
python -m uvicorn backend.credisense.api:app --reload
```

komutu ile servis ayağa kalkmalı ve `/health` cevap vermelidir.

## Faz 4: Raporlama ve Uzman İnceleme Akışı

Bu fazın amacı analiz sonucunu bir insanın hızlıca değerlendirebileceği hale getirmektir.

Yapılacaklar:

- [ ] Rapor formatını karar özeti, belge özeti, finansal göstergeler ve uyarılar olarak sabitle.
- [ ] Başvuruya tekil analiz ID'si ver.
- [ ] Rapor dosya adlarını analiz ID'si ile üret.
- [ ] Uzman incelemesi gereken kararları açıkça işaretle.
- [ ] Raporların JSON şemasını dokümante et.

Başarı ölçütü:

- Aynı analiz çıktısı hem terminalde hem API'de aynı ana alanları taşımalı.
- Uzman kişi `decision_summary`, `flags` ve `reasons` alanlarına bakarak hızlı karar verebilmeli.

## Faz 5: Model ve Veri Olgunluğu

Bu fazın amacı baseline formülün yanına daha güvenilir, izlenebilir bir model akışı koymaktır.

Yapılacaklar:

- [ ] Ham veri indirme ve dönüştürme komutlarını test altına al.
- [ ] Eğitim sırasında veri satır sayısı, sınıf dağılımı ve eksik değer özetini kaydet.
- [ ] Cross-validation ekle.
- [ ] Threshold seçimini metriklerle açıklanabilir hale getir.
- [ ] Model dosyasına versiyon, eğitim tarihi ve feature listesi metadatası ekle.
- [ ] Eğitim sonucunu `modeller/risk_modeli_sonuclari.json` içinde okunabilir raporla.

Başarı ölçütü:

- Model üretildiyse `risk.decision_source` alanı uygun giriş kapsamında `trained_model` olabilmeli.
- Model yoksa sistem kontrollü şekilde `baseline_formula` ile devam etmeli.

## Faz 6: Güvenlik ve Uyum

Bu fazın amacı sistemi gerçek kullanıcı belgelerine yaklaşmadan önce daha güvenli hale getirmektir.

Yapılacaklar:

- [ ] Yüklenen dosyalar için boyut ve uzantı kontrolü ekle.
- [ ] Kişisel veri içeren alanlar için maskeleme stratejisi belirle.
- [ ] Raporlarda hangi alanların saklanacağına karar ver.
- [ ] Audit log tasarımı yap.
- [ ] KVKK/GDPR için veri saklama ve silme politikasını dokümante et.

Başarı ölçütü:

- Sistem hangi veriyi aldığı, ne kadar tuttuğu ve hangi kararı neden verdiği konusunda izlenebilir olmalı.

## Önerilen Geliştirme Sırası

Yeni bir işe başlarken şu sırayı takip edin:

1. `python -m pytest` ile mevcut durumun temiz olduğunu doğrula.
2. Küçük bir değişiklik yap.
3. İlgili teste yeni senaryo ekle.
4. `python -m pytest` komutunu tekrar çalıştır.
5. README veya bu yol haritası değişiklikten etkileniyorsa güncelle.

Bu düzen, proje büyüdükçe neyin çalıştığını ve neyin eksik olduğunu görünür tutar.
