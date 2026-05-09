# Proje Ön Hazırlık Dosyası

## 1. Çalışmanın Başlığı

**CrediSense AI: Katmanlı Yapay Zeka ile Kredi Risk ve Finansal Belge Analizi**

Bu başlıkta projenin hem uygulama alanı hem de yapay zeka yönü belirtilmektedir. Projenin uygulama alanı kredi risk değerlendirmesidir. Yapay zeka yönü ise finansal belge anlama, anomali tespiti, davranışsal finans özellik çıkarımı ve makine öğrenmesi tabanlı risk tahminidir.

## 2. Özet

Bu çalışmada, kullanıcıdan alınan finansal belgeleri analiz ederek kredi riskini tahmin eden web tabanlı bir yapay zeka sistemi tasarlanması amaçlanmaktadır. Sistem, kimlik belgesi, maaş bordrosu ve banka hesap dökümü gibi PDF belgelerini doğrudan karar modeline vermek yerine katmanlı bir yapıda işler. İlk katmanda belgelerden gerekli bilgiler çıkarılır. İkinci katmanda belgeler arasında tutarlılık olup olmadığı ve şüpheli durumlar kontrol edilir. Üçüncü katmanda banka hesap hareketlerinden gelir düzeni, harcama oranı, nakit akışı ve bakiye davranışı gibi finansal özellikler üretilir. Son katmanda ise bu bilgiler kullanılarak kullanıcının kredi risk skoru tahmin edilir.

Bu problem önemlidir çünkü kredi başvurularında belgelerin manuel incelenmesi zaman alıcıdır ve değerlendirme sürecinde hatalara yol açabilir. Yapay zeka yöntemleri, belge işleme ve risk tahmini süreçlerini daha sistematik hale getirebilir. Bu çalışma kapsamında Lojistik Regresyon, Random Forest, XGBoost, LightGBM, anomali tespiti yöntemleri ve SHAP gibi açıklanabilir yapay zeka yaklaşımları incelenmiştir. Proje sonunda kullanıcıya düşük, orta veya yüksek risk seviyesi üreten ve bu kararın nedenlerini açıklayan bir karar destek sistemi geliştirilmesi hedeflenmektedir.

## 3. Giriş

Finans sektöründe kredi başvurularının değerlendirilmesi önemli ve dikkat gerektiren bir süreçtir. Bankalar ve finans kuruluşları, kredi başvurusu yapan kişilerin gelir durumunu, mevcut borçlarını, ödeme alışkanlıklarını ve finansal geçmişini inceleyerek karar verir. Bu süreçte yalnızca kullanıcının beyan ettiği bilgiler değil, kimlik belgesi, maaş bordrosu ve banka hesap dökümü gibi belgeler de değerlendirilir.

Geleneksel değerlendirme süreçlerinde bu belgelerin önemli bir bölümü uzmanlar tarafından manuel olarak kontrol edilir. Bu durum hem zaman kaybına neden olabilir hem de farklı uzmanların farklı yorumlar yapmasına yol açabilir. Ayrıca sahte belge, eksik belge, belgeler arası uyumsuzluk veya olağandışı finansal hareketler gibi durumların sistematik şekilde tespit edilmesi gerekir.

Yapay zeka bu problem için uygun bir yaklaşımdır çünkü sistem hem belgelerden bilgi çıkarabilir hem de çıkarılan bilgilerden risk tahmini yapabilir. Belge anlama yöntemleri PDF veya görüntü formatındaki belgelerden metin ve tablo bilgilerini çıkarabilir. Makine öğrenmesi algoritmaları ise gelir, harcama, borç oranı ve tutarlılık gibi özelliklerden yararlanarak risk sınıflandırması yapabilir.

Bu projede amaç, gerçek bir banka sisteminin birebir aynısını yapmak değildir. Amaç, kredi ön değerlendirme sürecinin yapay zeka ile nasıl desteklenebileceğini gösteren uygulanabilir bir öğrenci projesi ortaya koymaktır.

## 4. Problem Tanımı

Bu projede çözülmek istenen problem, kullanıcıdan alınan finansal belgeler ve form bilgileri kullanılarak kredi riskinin otomatik olarak tahmin edilmesidir. Problem tek bir yapay zeka probleminden oluşmamaktadır. Belge anlama, tutarlılık kontrolü, anomali tespiti ve risk sınıflandırma alt problemleri birlikte ele alınmaktadır.

Kullanılacak giriş verileri şunlardır:

| Girdi | Tür | Açıklama |
|---|---|---|
| Kimlik belgesi | PDF / görüntü | Kullanıcının kimlik bilgilerini doğrulamak için kullanılır. |
| Maaş bordrosu / gelir belgesi | PDF | Kullanıcının gelir durumunu analiz etmek için kullanılır. |
| Banka hesap dökümü | PDF | Son 3-6 aylık gelir, gider ve nakit akışı davranışlarını analiz etmek için kullanılır. |
| Talep edilen kredi tutarı | Form verisi | Geri ödeme kapasitesi ile karşılaştırılır. |
| Vade süresi | Form verisi | Aylık ödeme yükünü değerlendirmek için kullanılır. |
| Meslek ve gelir beyanı | Form verisi | Belgelerden çıkarılan bilgilerle karşılaştırılır. |
| Mevcut borç bilgileri | Form verisi / ek belge | Borç yükü oranını hesaplamak için kullanılır. |

Sistemin üretmesi beklenen çıktılar şunlardır:

| Çıktı | Açıklama |
|---|---|
| Risk skoru | 0 ile 1 arasında sayısal kredi riski değeri. |
| Risk seviyesi | Düşük, orta veya yüksek risk sınıfı. |
| Belge güven skoru | Belgelerden çıkarılan verinin güvenilirlik düzeyi. |
| Tutarlılık skoru | Belgeler arası bilgilerin ne kadar uyumlu olduğunu gösterir. |
| Anomali skoru | Şüpheli veya olağandışı finansal hareketleri gösterir. |
| Karar açıklaması | Risk skorunu etkileyen temel faktörleri açıklar. |

Bu problem temel olarak makine öğrenmesi tabanlı bir sınıflandırma problemidir. Risk skoru sayısal olarak üretildiği için regresyon benzeri bir yaklaşım da kullanılabilir. Ayrıca belge anlama tarafında doğal dil işleme ve doküman işleme, banka hareketleri tarafında ise anomali tespiti kullanılacaktır.

Bu sistem bankalar, finans kuruluşları ve kredi tahsis uzmanları için karar destek aracı olarak fayda sağlayabilir. Ancak sistemin nihai kredi onayı veren tek mekanizma olması değil, uzmanı destekleyen açıklanabilir bir ön değerlendirme sistemi olması hedeflenmektedir.

## 5. Literatür Taraması

Bu bölümde kredi risk tahmini, makine öğrenmesi algoritmaları, açıklanabilir yapay zeka ve belge anlama alanlarıyla ilişkili çalışmalar incelenmiştir. CrediSense AI yalnızca klasik kredi skorlama modeli değildir. Bu nedenle literatür taramasında hem kredi riski hem de belge işleme tarafındaki çalışmalar birlikte değerlendirilmiştir.

| No | Çalışma | Yıl | Veri Seti / Alan | Yöntem | Temel Sonuç | Güçlü Yön | Sınırlılık |
|---|---|---:|---|---|---|---|---|
| 1 | Lessmann, Baesens, Seow ve Thomas, "Benchmarking state-of-the-art classification algorithms for credit scoring" | 2015 | 8 gerçek kredi skorlama veri seti | 41 farklı sınıflandırma algoritması | Kredi skorlama için farklı algoritmaların kapsamlı karşılaştırması yapılmıştır. | Çok sayıda modeli karşılaştırdığı için kredi skorlama alanında güçlü bir referanstır. | Belge anlama veya PDF işleme kısmını ele almamaktadır. |
| 2 | Brown ve Mues, "An experimental comparison of classification algorithms for imbalanced credit scoring data sets" | 2012 | Gerçek kredi skorlama veri setleri | Lojistik Regresyon, Random Forest, SVM, Gradient Boosting vb. | Dengesiz veri probleminin kredi skorlama performansını etkilediği gösterilmiştir. | Kredi riskinde sınıf dengesizliği konusunu açık şekilde incelemiştir. | Model açıklanabilirliği ve belge analizi tarafı sınırlıdır. |
| 3 | Chen ve Guestrin, "XGBoost: A Scalable Tree Boosting System" | 2016 | Büyük ölçekli tablosal veri problemleri | XGBoost | Ağaç tabanlı boosting modelinin yüksek başarı ve ölçeklenebilirlik sağladığı gösterilmiştir. | Tablosal verilerde güçlü ve yaygın kullanılan bir yöntemdir. | Doğrudan kredi belgeleri veya açıklanabilirlik odaklı değildir. |
| 4 | Ke ve arkadaşları, "LightGBM: A Highly Efficient Gradient Boosting Decision Tree" | 2017 | Büyük ölçekli makine öğrenmesi veri setleri | LightGBM | Gradient boosting sürecinin daha hızlı ve verimli yapılabileceği gösterilmiştir. | Büyük veri setlerinde hızlı eğitim avantajı vardır. | Küçük öğrenci projesi verilerinde XGBoost'a göre farkı sınırlı olabilir. |
| 5 | Lundberg ve Lee, "A Unified Approach to Interpreting Model Predictions" | 2017 | Farklı makine öğrenmesi problemleri | SHAP | Karmaşık modellerin kararlarını özellik katkılarıyla açıklayan bir yaklaşım sunulmuştur. | Kredi riski gibi açıklanabilirlik isteyen alanlar için uygundur. | SHAP çıktılarının doğru yorumlanması kullanıcıya bırakılır. |
| 6 | Xu ve arkadaşları, "LayoutLM: Pre-training of Text and Layout for Document Image Understanding" | 2020 | Form, fiş ve doküman anlama veri setleri | LayoutLM | Metin ve sayfa düzenini birlikte kullanan belge anlama yaklaşımı önerilmiştir. | PDF ve taranmış belgelerden bilgi çıkarma açısından proje ile ilişkilidir. | İlk prototip için uygulaması OCR ve kurallara göre daha zor olabilir. |

Literatür taramasından çıkarılan sonuç şudur: Kredi risk tahmini için Lojistik Regresyon, Random Forest, XGBoost ve LightGBM gibi makine öğrenmesi modelleri kullanılabilir. Ancak bu çalışmaların çoğu doğrudan PDF belge anlama ve belgeler arası tutarlılık kontrolünü birlikte ele almamaktadır. CrediSense AI projesinin farkı, kredi risk modelini belge anlama ve anomali kontrolü katmanlarıyla birlikte tasarlamasıdır.

## 6. İncelenen Yöntemler ve Algoritmalar

Bu bölümde proje kapsamında kullanılabilecek yapay zeka yöntemleri açıklanmaktadır. Yalnızca algoritma adı vermek yeterli olmadığı için her yöntemin temel mantığı ve projedeki kullanım amacı belirtilmiştir.

### 6.1 Lojistik Regresyon

Lojistik Regresyon, sınıflandırma problemlerinde kullanılan temel bir makine öğrenmesi algoritmasıdır. Girdi özellikleri ile hedef sınıf arasındaki ilişkiyi matematiksel olarak modellemeye çalışır. Örneğin gelir, borç oranı, harcama oranı ve tutarlılık skoru gibi değerlerden yararlanarak kullanıcının düşük riskli veya yüksek riskli olup olmadığını tahmin edebilir.

Bu proje için avantajı, basit ve açıklanabilir olmasıdır. İlk karşılaştırma modeli olarak kullanılabilir. Sınırlılığı ise karmaşık ilişkileri Random Forest veya XGBoost kadar iyi yakalayamayabilmesidir.

### 6.2 Random Forest

Random Forest, birden fazla karar ağacının birlikte çalıştığı bir makine öğrenmesi yöntemidir. Tek bir karar ağacı yerine birçok karar ağacı oluşturur ve bu ağaçların ortak kararına göre tahmin yapar. Bu sayede tek bir ağacın hatalı veya aşırı öğrenmiş karar vermesi azaltılabilir.

Bu projede Random Forest, gelir düzenliliği, harcama/gelir oranı, anomali skoru ve tutarlılık skoru gibi farklı özellikleri birlikte değerlendirmek için kullanılabilir. Tablosal verilerde başarılı sonuçlar verebilen bir yöntemdir.

### 6.3 XGBoost

XGBoost, karar ağaçlarını sırayla güçlendirerek çalışan gelişmiş bir gradient boosting algoritmasıdır. Her yeni ağaç, önceki ağaçların yaptığı hataları azaltmaya çalışır. Bu nedenle tablosal veri problemlerinde sık kullanılan güçlü bir yöntemdir.

Kredi risk tahmini genellikle tablosal özelliklere dayandığı için XGBoost bu proje için uygun bir adaydır. Özellikle davranışsal finans özellikleri ve tutarlılık skorları bir araya getirildiğinde başarılı sonuç verebilir.

### 6.4 LightGBM

LightGBM, XGBoost'a benzer şekilde gradient boosting mantığıyla çalışan hızlı ve verimli bir algoritmadır. Büyük veri setlerinde daha kısa eğitim süresi sağlayabilir. Özellikle çok sayıda özellik olduğunda avantajlı olabilir.

Bu projede veri miktarı çok büyük olmayacağı için LightGBM ilk aşamada zorunlu değildir. Ancak XGBoost ile karşılaştırma yapmak için denenebilir.

### 6.5 Anomali Tespiti

Anomali tespiti, normal davranıştan farklı olan durumları belirlemek için kullanılır. Banka hesap hareketlerinde olağandışı yüksek para girişleri, düzensiz maaş yatışları veya ani bakiye değişimleri anomali olarak değerlendirilebilir.

Bu projede başlangıç için kural tabanlı eşikler kullanılabilir. Daha sonra Isolation Forest gibi makine öğrenmesi tabanlı anomali tespiti yöntemleri denenebilir.

### 6.6 OCR ve Belge Anlama

OCR, görüntü veya taranmış PDF içindeki metni okunabilir metne dönüştürme işlemidir. Belge anlama ise yalnızca metni çıkarmakla kalmaz, metnin hangi alana ait olduğunu anlamaya çalışır. Örneğin bir bordro belgesinde "net maaş", "işveren", "dönem" gibi alanların bulunması belge anlama problemidir.

Bu projede ilk prototipte OCR, PDF metin çıkarımı, tablo ayrıştırma ve kural tabanlı alan çıkarımı kullanılabilir. Daha gelişmiş aşamada LayoutLM gibi belge anlama modelleri değerlendirilebilir.

### 6.7 SHAP ile Açıklanabilirlik

SHAP, modelin verdiği tahminde hangi özelliklerin ne kadar etkili olduğunu açıklamak için kullanılan bir yöntemdir. Örneğin model yüksek risk sonucu verdiyse, bu sonucun yüksek harcama/gelir oranı, düşük gelir düzenliliği veya belge tutarsızlığı nedeniyle oluştuğu gösterilebilir.

Kredi risk değerlendirmesinde açıklanabilirlik önemli olduğu için SHAP bu proje için uygun bir yöntemdir.

### 6.8 Bu Proje İçin En Uygun Yaklaşım

İlk prototip için en uygun yaklaşım şu şekilde görülmektedir:

- Belge alan çıkarımı için OCR + PDF metin çıkarımı + kurallar
- Tutarlılık kontrolü için kural tabanlı karşılaştırmalar
- Anomali kontrolü için basit eşik değerleri ve istatistiksel kontroller
- Risk tahmini için Lojistik Regresyon, Random Forest ve XGBoost karşılaştırması
- Açıklanabilirlik için SHAP

Bu yaklaşım öğrenci projesi için uygulanabilir görünmektedir. Daha gelişmiş belge anlama modelleri ve büyük ölçekli derin öğrenme yöntemleri ikinci aşama geliştirmesi olarak ele alınabilir.

## 7. Veri Seti Araştırması

Bu projede gerçek banka belgelerine ve müşteri verilerine erişim sınırlı olabileceği için açık veri setleri ve sentetik veri birlikte kullanılacaktır. Kredi risk tahmini için açık veri setleri kullanılabilir. Belge anlama ve tutarlılık kontrolü için ise sentetik PDF belgeleri oluşturulabilir.

| Veri Seti | Kaynak | Veri Türü | Örnek Sayısı | Hedef Değişken | Uygunluk |
|---|---|---|---:|---|---|
| Statlog German Credit Data | UCI Machine Learning Repository | Tablo | 1.000 | İyi/kötü kredi riski | Kredi risk sınıflandırması için uygundur. |
| Give Me Some Credit | Kaggle | Tablo | Yaklaşık 150.000 kayıt veya farklı hazırlanmış sürümlerde 112.915 kayıt | Finansal sıkıntı / temerrüt olasılığı | Kredi skorlama modeli için uygundur. |
| South German Credit | UCI Machine Learning Repository | Tablo | 1.000 | İyi/kötü kredi riski | German Credit verisinin düzenlenmiş bir sürümü olarak değerlendirilebilir. |
| Sentetik maaş bordrosu belgeleri | Proje kapsamında üretilecek | PDF / tablo | Proje ihtiyacına göre | Belge alanları | Belge anlama katmanı için uygundur. |
| Sentetik banka hesap dökümleri | Proje kapsamında üretilecek | PDF / tablo | Proje ihtiyacına göre | İşlem hareketleri | Davranışsal finans özellikleri için uygundur. |

Veri setlerinde bulunabilecek temel özellikler şunlardır:

- Yaş
- Gelir
- Kredi tutarı
- Vade süresi
- Mevcut kredi sayısı
- Borç oranı
- Gecikme veya temerrüt bilgisi
- Harcama ve ödeme davranışı

Bu açık veri setleri doğrudan PDF belge içermediği için belge anlama katmanı için yeterli değildir. Bu nedenle proje kapsamında örnek kimlik, bordro ve banka dökümü şablonları oluşturulması planlanmaktadır. Bu belgelerden çıkarılan alanlar daha sonra açık veri setlerinden gelen kredi risk özellikleriyle birleştirilebilir.

## 8. Veri Ön İşleme Planı

Bu projede farklı veri türleri kullanılacağı için ön işleme adımları birkaç gruba ayrılmaktadır.

### 8.1 PDF ve Belge Ön İşleme

- PDF dosyasının okunabilir olup olmadığının kontrol edilmesi
- Taranmış belge ise OCR uygulanması
- Metin ve tablo alanlarının ayrıştırılması
- Kimlik, maaş ve banka dökümü gibi belge türlerinin sınıflandırılması
- Eksik veya okunamayan alanların işaretlenmesi
- Her belge için güven skoru üretilmesi

### 8.2 Tablo Verileri İçin Ön İşleme

- Eksik değerlerin kontrol edilmesi
- Aykırı değerlerin incelenmesi
- Kategorik değişkenlerin sayısallaştırılması
- Sayısal değişkenlerin normalize veya standart hale getirilmesi
- Eğitim ve test verisine ayrılması
- Sınıf dengesizliği varsa SMOTE, ağırlıklı sınıflandırma veya uygun metrik seçimi gibi çözümlerin değerlendirilmesi

### 8.3 Banka Hareketleri İçin Ön İşleme

- İşlem tarihinin standart formata dönüştürülmesi
- Gelir ve gider hareketlerinin ayrılması
- Aylık toplam gelir ve giderlerin hesaplanması
- Harcama/gelir oranının çıkarılması
- Ortalama bakiye ve ay sonu bakiye eğiliminin hesaplanması
- Olağandışı yüksek işlem tutarlarının belirlenmesi

### 8.4 Metin Verileri İçin Ön İşleme

- Küçük harfe çevirme
- Gereksiz karakterleri temizleme
- Alan adlarını standartlaştırma
- Belge içinde anahtar kelime arama
- Gerekirse kelime veya cümle temsili oluşturma

Bu ön işleme adımları tamamlandığında sistem ham PDF dosyaları yerine model tarafından kullanılabilecek yapılandırılmış veriyle çalışacaktır.

## 9. Önerilen Proje Yaklaşımı

Bu projede katmanlı bir yapay zeka mimarisi önerilmektedir. Sistem, tek bir modelin tüm işi yapması yerine her aşamada farklı bir sorumluluğa sahip modüllerden oluşacaktır.

Genel veri akışı şu şekildedir:

```text
PDF Belgeleri + Kullanıcı Form Verileri
        |
        v
Belge Anlama Katmanı
        |
        v
Tutarlılık ve Anomali Katmanı
        |
        v
Davranışsal Finans Özellik Katmanı
        |
        v
Nihai Risk Tahmin Katmanı
        |
        v
Risk Skoru + Risk Seviyesi + Açıklamalar
```

### 9.1 Belge Anlama Katmanı

Bu katman kullanıcıdan alınan kimlik belgesi, maaş bordrosu ve banka hesap dökümünü işler. Amaç, PDF belgelerinden gerekli bilgileri çıkararak yapılandırılmış veri oluşturmaktır.

Bu katmanda çıkarılabilecek bilgiler:

- Kimlik belgesinden ad, soyad, TCKN ve doğum tarihi
- Maaş bordrosundan net maaş, işveren, dönem ve çalışan adı
- Banka dökümünden işlem tarihi, açıklama, tutar, bakiye ve işlem yönü

İlk prototipte OCR, PDF metin çıkarımı, tablo ayrıştırma ve kural tabanlı alan yakalama yöntemleri kullanılacaktır.

### 9.2 Tutarlılık ve Anomali Katmanı

Bu katman belgelerden çıkarılan bilgilerin birbiriyle uyumlu olup olmadığını kontrol eder.

Örnek kontroller:

- Kimlikteki ad-soyad ile bordrodaki ad-soyad eşleşiyor mu?
- Bordrodaki maaş banka hesabına düzenli şekilde yatıyor mu?
- Kullanıcının beyan ettiği gelir ile belgelerdeki gelir uyumlu mu?
- Banka hesabında olağandışı yüksek para girişi veya çıkışı var mı?
- Belgede okunamayan veya eksik alan var mı?

Bu katman sonunda tutarlılık skoru, anomali skoru ve şüpheli durum listesi üretilecektir.

### 9.3 Davranışsal Finans Özellik Katmanı

Bu katman banka hesap hareketlerinden finansal davranış özellikleri üretir. Amaç, kullanıcının yalnızca beyan ettiği geliri değil, gerçek finansal alışkanlıklarını da modele dahil etmektir.

Üretilebilecek özellikler:

| Özellik | Açıklama |
|---|---|
| Ortalama aylık gelir | Son aylardaki düzenli gelir ortalaması. |
| Gelir düzenliliği | Maaş girişlerinin zaman ve tutar bakımından istikrarı. |
| Harcama/gelir oranı | Aylık giderlerin gelire oranı. |
| Ortalama bakiye | Hesapta tutulan ortalama bakiye. |
| Nakit akışı dalgalanması | Gelir ve gider hareketlerinin ne kadar değişken olduğu. |
| Borç/gelir oranı | Mevcut borçların gelire oranı. |
| Büyük işlem oranı | Olağandışı büyük işlemlerin toplam işlemlere oranı. |

### 9.4 Nihai Risk Tahmin Katmanı

Bu katman önceki katmanlardan gelen tüm bilgileri birleştirir ve kredi riskini tahmin eder. Modelin girdileri belge güven skoru, tutarlılık skoru, anomali skoru, davranışsal finans özellikleri ve kullanıcı form bilgileri olacaktır.

Denenebilecek algoritmalar:

- Lojistik Regresyon
- Random Forest
- XGBoost
- LightGBM

Model çıktısı şu şekilde olacaktır:

- Risk skoru: 0 ile 1 arasında
- Risk seviyesi: düşük, orta veya yüksek
- Karar açıklaması: risk skorunu etkileyen temel nedenler

Örnek risk seviyesi aralıkları:

| Risk Skoru | Risk Seviyesi |
|---|---|
| 0.00 - 0.33 | Düşük risk |
| 0.34 - 0.66 | Orta risk |
| 0.67 - 1.00 | Yüksek risk |

Bu aralıklar ilk prototip için örnek olarak verilmiştir. Gerçek model eğitildikten sonra eşikler veri setine göre yeniden düzenlenebilir.

### 9.5 Web Arayüzü

Projede basit bir web arayüzü bulunması planlanmaktadır. Kullanıcı bu arayüz üzerinden belgelerini PDF formatında yükleyebilecektir. Sistem analiz tamamlandıktan sonra risk skoru, risk seviyesi, belge durumu ve açıklamaları gösterecektir. Ayrıca uzman panelinde başvuru özeti, tutarlılık uyarıları ve model açıklamaları yer alacaktır.

## 10. Model Değerlendirme Ölçütleri

Bu projede model başarısı yalnızca accuracy ile değerlendirilmemelidir. Kredi riski gibi problemlerde riskli başvuruların kaçırılmaması önemlidir. Bu nedenle farklı ölçütler birlikte kullanılacaktır.

Sınıflandırma modeli için kullanılabilecek metrikler:

| Metrik | Açıklama |
|---|---|
| Accuracy | Modelin toplam doğru tahmin oranını gösterir. |
| Precision | Riskli olarak tahmin edilen başvuruların ne kadarının gerçekten riskli olduğunu gösterir. |
| Recall | Gerçek riskli başvuruların ne kadarının model tarafından yakalandığını gösterir. |
| F1-score | Precision ve recall değerlerinin dengeli ortalamasıdır. |
| Confusion Matrix | Doğru ve yanlış sınıflandırmaları ayrıntılı gösterir. |
| ROC-AUC | Modelin sınıfları ayırma başarısını ölçer. |

Belge anlama katmanı için kullanılabilecek ölçütler:

- Belge türü sınıflandırma doğruluğu
- Alan çıkarımı doğruluğu
- OCR hata oranı
- Tablo çıkarımı başarısı

Tutarlılık ve anomali katmanı için kullanılabilecek ölçütler:

- Doğru tespit edilen uyumsuzluk oranı
- Yanlış alarm oranı
- Şüpheli işlem tespit başarısı

Bu metrikler sayesinde sistemin yalnızca risk tahmin başarısı değil, belge işleme ve anomali tespiti başarısı da ayrı ayrı değerlendirilebilir.

## 11. Beklenen Sonuçlar

Proje sonunda kullanıcının yüklediği finansal belgelerden bilgi çıkaran, belgeler arası tutarlılığı kontrol eden ve kredi riskini tahmin eden web tabanlı bir karar destek sistemi geliştirilmesi beklenmektedir.

Beklenen çıktılar:

- Kullanıcı için 0 ile 1 arasında risk skoru
- Düşük, orta veya yüksek risk seviyesi
- Belge güven ve tutarlılık durumu
- Banka hareketlerine dayalı finansal davranış özeti
- Risk skorunu etkileyen temel nedenler
- Uzman paneli için başvuru değerlendirme özeti

Bu projenin güçlü yönü, kredi risk tahminini yalnızca tablosal veriyle değil, belge anlama ve finansal davranış analiziyle birlikte ele almasıdır. Sınırlılığı ise gerçek banka verilerine erişim zor olduğu için ilk aşamada açık veri setleri ve sentetik belgelerle çalışılacak olmasıdır. Ayrıca sistemin çıktıları nihai kredi onayı olarak değil, karar destek amacıyla değerlendirilmelidir.

## 12. Kaynakça

[1] Lessmann, S., Baesens, B., Seow, H. V., & Thomas, L. C. (2015). Benchmarking state-of-the-art classification algorithms for credit scoring: An update of research. *European Journal of Operational Research, 247*(1), 124-136. https://doi.org/10.1016/j.ejor.2015.05.030

[2] Brown, I., & Mues, C. (2012). An experimental comparison of classification algorithms for imbalanced credit scoring data sets. *Expert Systems with Applications, 39*(3), 3446-3453. https://doi.org/10.1016/j.eswa.2011.09.033

[3] Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*. https://www.kdd.org/kdd2016/papers/files/rfp0697-chenAemb.pdf

[4] Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., & Liu, T. Y. (2017). LightGBM: A highly efficient gradient boosting decision tree. *Advances in Neural Information Processing Systems 30*. https://papers.nips.cc/paper/6907-lightgbm-a-highly-efficient-gradient-boosting-decision-tree

[5] Lundberg, S. M., & Lee, S. I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems 30*. https://neurips.cc/virtual/2017/poster/9253

[6] Xu, Y., Li, M., Cui, L., Huang, S., Wei, F., & Zhou, M. (2020). LayoutLM: Pre-training of text and layout for document image understanding. *Proceedings of the 26th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*. https://www.kdd.org/kdd2020/accepted-papers/view/layoutlm-pre-training-of-text-and-layout-for-document-image-understanding.html

[7] UCI Machine Learning Repository. (1994). Statlog German Credit Data. https://archive-beta.ics.uci.edu/dataset/144/statlog%2Bgerman%2Bcredit%2Bdata

[8] Kaggle. (2011). Give Me Some Credit Competition Data. https://www.kaggle.com/datasets/brycecf/give-me-some-credit-dataset
