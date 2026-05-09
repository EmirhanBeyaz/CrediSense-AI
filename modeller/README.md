# Modeller

Bu klasör, eğitim sonucunda üretilen model ve metrik dosyalarını saklamak için kullanılır.

İlk eğitim komutu:

```powershell
python -B -m backend.credisense.model_egitimi
```

Beklenen çıktılar:

| Dosya | Açıklama |
|---|---|
| `risk_modeli.pkl` | En iyi bulunan model ve özellik kolonları |
| `risk_modeli_sonuclari.json` | Model karşılaştırma metrikleri |

