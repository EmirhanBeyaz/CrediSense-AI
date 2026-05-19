# CrediSense AI Frontend

Bu klasor, Stitch tarafindan verilen HTML ekran seti referans alinarak Next.js, TypeScript ve Tailwind CSS ile component tabanli frontend uygulamasina donusturulmustur.

## Teknoloji

- Next.js
- React
- TypeScript
- Tailwind CSS
- Merkezi service katmani

## Calistirma

```bash
cd frontend
npm install
npm run dev
```

Varsayilan frontend adresi:

```text
http://localhost:3000
```

Backend varsayilan adresi:

```text
http://127.0.0.1:8000
```

`.env.example` dosyasindan `.env.local` olusturup backend adresini degistirebilirsiniz.

## Roller

- Musteri
- Banka Uzmani

Login sonrasi menuler role gore ayrilir. Musteri banka uzman panelini, banka uzmani musteri basvuru/odeme ekranlarini gormez.

## Service Katmani

API istekleri component icine yazilmaz. Backend baglantilari `src/services` altindadir:

- `authService`
- `applicationService`
- `documentService`
- `analysisService`
- `expertService`
- `reportService`
- `assistantService`
- `paymentService`

Endpoint pathleri `src/lib/endpoints.ts` dosyasindan merkezi olarak yonetilir.

## Backend Baglantisi

Next rewrite kullanilir:

```text
/api/backend/* -> CREDISENSE_BACKEND_URL/*
```

Tarayici CORS problemi yasamasin diye frontend varsayilan olarak `/api/backend` uzerinden proxy kullanir.

## Test Girisleri

Backend ilk calistiginda SQLite kullanici veritabanina asagidaki test kullanicilarini ekler:

- Musteri: `deniz.kaya` / `123456`
- Banka uzmani: `uzman@bank.test` / `123456`

## Not

Mock veriler sadece backend ayakta degilken demo/fallback icin kullanilir. Asil analiz, basvuru, karar ve asistan akislari backend API servislerine istek atacak sekilde yazilmistir.
