# CrediSense AI Ürün Akışı Mimarisi

Bu doküman, belge analizi dışında kalan ürün akışını açıklar. Amaç, sistemin sadece risk skoru
üreten bir kod parçası değil, kullanıcı ve banka tarafı olan bir ürün gibi çalışmasını sağlamaktır.

## 1. Başvuru Aşamaları

1. Kullanıcı başvuru formunu doldurur.
2. Kullanıcı KVKK ve veri işleme onaylarını verir.
3. Kullanıcı zorunlu belgeleri yükler.
4. Sistem başvuru paketini, formu ve onayları kontrol eder.
5. Sistem belge analizi, tutarlılık kontrolü ve risk tahmini yapar.
6. Sistem kullanıcı ve banka için ayrı çıktılar üretir.

## 2. Üretilen Ana Çıktılar

| Çıktı | Kullanım Amacı |
|---|---|
| application_package_quality | Zorunlu belgeler var mı, PDF okunabiliyor mu, belge paketi analiz edilebilir mi? |
| application_form_quality | Başvuru formu eksik veya hatalı alan içeriyor mu? |
| consent_quality | KVKK ve veri işleme onayları alınmış mı? |
| application_status | Başvurunun genel ürün durum kodu. |
| user_view | Kullanıcının göreceği sade başvuru sonucu. |
| bank_view | Banka uzmanının göreceği teknik özet ve önerilen aksiyon. |
| application_record | Başvurunun ID, durum, başvuru sahibi ve durum geçmişi kaydı. |

## 3. Durum Kodları

| Durum Kodu | Anlamı |
|---|---|
| CONSENT_REQUIRED | Gerekli onaylar eksik veya reddedilmiş. |
| DOCUMENT_REVISION_REQUIRED | Eksik veya okunamayan zorunlu belge var. |
| FORM_REVISION_REQUIRED | Başvuru formunda eksik veya hatalı alan var. |
| PRE_APPROVED | Başvuru ön onaya uygun görünüyor. |
| MANUAL_REVIEW | Başvuru banka uzmanı tarafından incelenmeli. |
| DEEP_REVIEW | Başvuru detaylı risk incelemesine alınmalı. |
| EXTRA_DOCUMENT_REQUESTED | Banka uzmanı kullanıcıdan ek belge istedi. |
| APPROVED | Banka uzmanı başvuruyu onayladı. |
| REJECTED | Banka uzmanı başvuruyu reddetti. |

## 4. Kullanıcı ve Banka Ayrımı

Kullanıcı tarafında risk skoru doğrudan gösterilmez. Kullanıcı sadece başvuru durumunu ve
kendisinden beklenen aksiyonu görür.

Banka tarafında risk skoru, risk seviyesi, model kaynağı, tutarlılık skoru, anomali skoru ve
başvuruyu durduran maddeler gösterilir. Bu ayrım, ürünün gerçek banka akışına daha yakın
çalışmasını sağlar.

## 5. Başvuru Kaydı

Her analiz sonucunda `APP-YYYYMMDD-XXXXXXXX` formatında bir `application_id` üretilir. Bu ID,
kullanıcı paneli, banka paneli, raporlar ve ileride eklenecek ödeme asistanı için ortak takip
anahtarıdır.

`application_record` içinde şu bilgiler tutulur:

| Alan | Açıklama |
|---|---|
| application_id | Başvurunun ürün içindeki takip numarası. |
| created_at | Başvurunun oluşturulma zamanı. |
| current_status | Başvurunun güncel durum kodu. |
| applicant | Başvuru sahibinin kısa kimlik özeti. |
| credit_request | Talep edilen kredi ve temel gelir/borç özeti. |
| risk_summary | Banka tarafında kullanılacak kısa risk özeti. |
| status_history | Başvurunun durum geçmişi. |

## 6. Banka Uzmanı Kararları

Banka uzmanı, analiz tamamlandıktan sonra başvuru kaydı üzerinde karar verebilir.

| Karar | Yeni Durum | Açıklama |
|---|---|---|
| approve | APPROVED | Kredi başvurusu onaylanır. |
| reject | REJECTED | Başvuru reddedilir. |
| request_extra_document | EXTRA_DOCUMENT_REQUESTED | Kullanıcıdan ek belge istenir. |
| send_to_deep_review | DEEP_REVIEW | Başvuru detaylı inceleme ekibine yönlendirilir. |

Bu kararlar `status_history` içine yeni olay olarak eklenir. Böylece başvurunun hangi aşamalardan
geçtiği ürün içinde takip edilebilir.

## 7. Kredi Sonrası Ödeme Planı ve Asistan

Kredi başvurusu `APPROVED` durumuna geldikten sonra ödeme planı oluşturulabilir. Ödeme planı,
başvuru kaydındaki kredi tutarı ve vade bilgisine göre üretilir.

| Çıktı | Açıklama |
|---|---|
| loan_id | Onaylanan kredi için üretilen takip numarası. |
| principal | Kredi ana para tutarı. |
| term_months | Vade ay sayısı. |
| monthly_payment | Tahmini aylık taksit. |
| total_payment | Toplam geri ödeme tutarı. |
| total_interest | Toplam faiz tutarı. |
| schedule | Taksit takvimi. |

Ödeme asistanı ilk aşamada kontrollü soru tipleriyle çalışır:

| Soru Tipi | Açıklama |
|---|---|
| summary | Kredi ve ödeme planı özetini verir. |
| next_payment | Sıradaki taksit tarihini ve tutarını gösterir. |
| remaining_debt | Tahmini kalan ana parayı gösterir. |
| early_payment | Erken ödeme için tahmini bilgi verir ve banka desteğine yönlendirir. |
| late_payment | Gecikme durumunda kullanıcıyı banka desteğine yönlendirir. |

Bu modül gerçek bankacılık işlemi yapmaz. Erken kapama, gecikme faizi ve yapılandırma gibi kesin
tutar gerektiren konularda kullanıcı banka desteğine yönlendirilir.

## 8. Kredi Sonrası Asistan İçin Genişletme

Kredi onaylandıktan sonra ayrı bir ödeme asistanı modülü eklenebilir. Bu modül mevcut risk
analizi katmanlarından ayrı tutulmalıdır. Ödeme asistanı; ödeme planı, taksit hatırlatma, erken
ödeme ve gecikme bilgilendirme gibi konulara odaklanmalıdır.
