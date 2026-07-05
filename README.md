<div align="center">

# ⚡ Upload-Hub

**بک‌اند کامل آپلود و دانلود فایل — با احراز هویت OTP، پنل مدیریت و ذخیره‌سازی ابری (ArvanCloud S3)**

یک سرویس آماده‌ی پرودАкشن که با **FastAPI** ساخته شده: کاربران ثبت‌نام و لاگین می‌کنند،
فایل‌ها را با یک نام دلخواه (تا ۲۰۰MB) آپلود می‌کنند، بقیه می‌توانند فایل‌ها را ببینند/سرچ/دانلود کنند،
و ادمین از یک پنل کامل همه‌چیز را مدیریت می‌کند.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![ArvanCloud](https://img.shields.io/badge/Storage-ArvanCloud%20S3-1B6AC6)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## 📖 معرفی

**Upload-Hub** بک‌اند یک وب‌سایت اشتراک‌گذاری فایل است. هر کاربرِ لاگین‌کرده می‌تواند فایل آپلود کند،
و همه‌ی کاربران می‌توانند فایل‌ها را جست‌وجو، مشاهده و دانلود کنند. فایل‌ها روی باکت
**S3-compatible آروان‌کلود** ذخیره می‌شوند و فقط متادیتای آن‌ها (نام، سایز، صاحب، نوع) در دیتابیس نگه‌داری می‌شود
تا لیست/سرچ سریع باشد.

- **احراز هویت** مبتنی بر OTP پیامکی + لاگین با موبایل/یوزرنیم (JWT با access/refresh token).
- **مدیریت فایل**: آپلود با سقف حجم، سرچ، دانلود با لینک موقت امن (presigned) یا لینک عمومی دائمی.
- **پنل ادمین**: مدیریت کاربران، نشست‌ها، بن، و **مدیریت کامل فایل‌ها + وضعیت مصرف باکت**.
- **کنترل سهمیه**: مجموع حجم فایل‌ها نمی‌تواند از سقف باکت (پیش‌فرض ۵GB) عبور کند.

> 💡 داده‌های دائمی در **SQLite** (قابل تعویض با PostgreSQL/MySQL) و داده‌های موقت
> (OTP، نشست‌ها، بن‌ها) در **Redis** با TTL نگه‌داری می‌شوند.

---

## ✨ امکانات

### 📁 آپلود و اشتراک فایل
- آپلود فایل با **نام دلخواه + توضیح** برای هر کاربر لاگین‌کرده
- **سقف حجم هر فایل: ۲۰۰MB** (قابل تنظیم) + آپلود خودکار multipart برای فایل‌های بزرگ
- **جست‌وجو** بر اساس نام، نام فایل و توضیح
- **دانلود** از طریق **Presigned URL** (لینک موقت امضاشده) یا **لینک عمومی دائمی** (حالت public-read)
- کنترل **سهمیه‌ی کل باکت** (پیش‌فرض ۵GB) — قبل از هر آپلود بررسی می‌شود
- هر کاربر فایل‌های خودش را ویرایش/حذف می‌کند؛ ادمین همه را

### 🔐 احراز هویت
- ثبت‌نام با **یوزرنیم، موبایل و پسورد** + **تأیید کد OTP** قبل از ساخت نهایی کاربر
- لاگین با **موبایل + پسورد** یا **یوزرنیم + پسورد** + فرم OAuth2 برای Swagger
- توکن **JWT** جداگانه برای access و refresh با **چرخش توکن (rotation)**
- **نرمال‌سازی خودکار شماره موبایل ایران** (`09...` → `+98...`)

### 🛡️ امنیت
- هش پسورد با **bcrypt**
- محدودیت **تلاش اشتباه OTP** و **cooldown** ارسال مجدد
- **محدودیت نشست‌های هم‌زمان** هر کاربر (حذف قدیمی‌ترین هنگام عبور از سقف)
- باطل‌سازی نشست: تکی، همه‌ی دستگاه‌ها (مثلاً بعد از تغییر پسورد یا بن)

### 🧑‍💼 پنل ادمین (`/admin`)
- مانیتورینگ منابع سیستم (CPU / RAM / Disk) و health چک (Redis + DB)
- مدیریت کاربران: بن/آنبن (موقت یا دائم)، فعال/غیرفعال‌سازی، باطل‌سازی نشست‌ها
- **مدیریت فایل‌ها**: لیست و سرچ، ویرایش نام/توضیح، حذف، دانلود
- **کارت وضعیت باکت**: مصرف از سهمیه، تعداد فایل، فضای آزاد و چک دسترسی زنده به باکت

---

## 🧱 پشته‌ی فناوری

| لایه | فناوری |
|------|--------|
| Web framework | FastAPI + Uvicorn |
| ORM / دیتابیس | SQLAlchemy 2.0 + SQLite |
| کش / داده‌ی موقت | Redis |
| ذخیره‌سازی فایل | ArvanCloud Object Storage (S3) via **boto3** |
| مهاجرت دیتابیس | Alembic |
| احراز هویت | python-jose (JWT) + bcrypt |
| اعتبارسنجی | Pydantic v2 |
| مانیتورینگ | psutil |
| استقرار | Docker + docker-compose |

---

## 📂 ساختار پروژه

```
upload-hub/
├── app/
│   ├── main.py                 # نقطه‌ی ورود FastAPI (وصل‌کردن routerها)
│   ├── database.py             # engine و session و Base
│   ├── core/
│   │   ├── config.py           # تنظیمات از .env
│   │   ├── security.py         # هش پسورد + JWT
│   │   ├── redis_client.py     # کلاینت Redis
│   │   └── request_info.py     # استخراج IP/مرورگر/دستگاه
│   ├── models/
│   │   ├── user.py             # مدل کاربر
│   │   └── file.py             # مدل فایل (متادیتا)
│   ├── schemas/
│   │   ├── auth.py             # اسکیمای احراز هویت
│   │   └── files.py            # اسکیمای فایل + وضعیت باکت
│   ├── routers/
│   │   ├── auth.py             # مسیرهای احراز هویت
│   │   ├── files.py            # مسیرهای آپلود/سرچ/دانلود
│   │   └── admin.py            # مسیرهای پنل ادمین
│   ├── services/
│   │   ├── otp.py              # منطق OTP + ثبت‌نام معلق
│   │   ├── tokens.py           # مدیریت نشست‌های refresh
│   │   ├── bans.py             # بن کاربران
│   │   ├── monitoring.py       # آمار سیستم و سلامت
│   │   └── storage.py          # ذخیره‌سازی S3 آروان (آپلود/دانلود/حذف)
│   └── static/admin.html       # رابط پنل ادمین
├── migrations/                 # مهاجرت‌های Alembic
├── scripts/create_admin.py     # ساخت/ارتقای کاربر ادمین
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── LEARN.md                    # راهنمای یادگیری قدم‌به‌قدم کد
```

---

## 🚀 نصب و راه‌اندازی

### پیش‌نیازها
- Python **3.11+**
- **Redis** در حال اجرا (لوکال یا Docker)
- یک **باکت ArvanCloud** به‌همراه Access Key و Secret Key
  (از [پنل آروان](https://panel.arvancloud.ir/storage/dashboard) بگیر)

### روش ۱ — اجرای محلی

```bash
# ۱) کلون پروژه
git clone https://github.com/<your-username>/upload-hub.git
cd upload-hub

# ۲) محیط مجازی و نصب وابستگی‌ها
python -m venv .venv
source .venv/bin/activate        # ویندوز: .venv\Scripts\activate
pip install -r requirements.txt

# ۳) ساخت فایل تنظیمات
cp .env.example .env
#  ← SECRET_KEY و مقادیر S3 (آروان) را حتماً پر کن

# ۴) اعمال مهاجرت‌های دیتابیس
alembic upgrade head

# ۵) اجرای سرور
uvicorn app.main:app --reload
```

سرویس بالا می‌آید:
- 📘 مستندات Swagger: **http://localhost:8000/docs**
- 🧑‍💼 پنل ادمین: **http://localhost:8000/admin**

### روش ۲ — با Docker Compose (پیشنهادی)

```bash
cp .env.example .env      # SECRET_KEY و مقادیر S3 را تنظیم کن
docker compose up --build
```

این دستور هم‌زمان **Redis** و **API** را بالا می‌آورد و به‌صورت خودکار
`alembic upgrade head` را اجرا می‌کند (جدول‌ها ساخته می‌شوند).

### ساخت کاربر ادمین

```bash
# ساخت ادمین جدید
python -m scripts.create_admin <username> <phone> <password>

# یا ارتقای یک کاربر موجود به ادمین
python -m scripts.create_admin --promote <username_or_phone>
```

---

## ⚙️ تنظیمات (متغیرهای محیطی)

| متغیر | پیش‌فرض | توضیح |
|-------|---------|-------|
| `APP_NAME` | `OTP Auth Service` | نام اپلیکیشن |
| `DEBUG` | `true` | حالت دیباگ (کد OTP در پاسخ برمی‌گردد) |
| `DATABASE_URL` | `sqlite:///./otp_auth.db` | آدرس دیتابیس |
| `REDIS_URL` | `redis://localhost:6379/0` | آدرس Redis |
| `max_session` | `3` | سقف نشست‌های هم‌زمان هر کاربر |
| `SECRET_KEY` | — | **کلید امضای JWT (حتماً عوض شود!)** |
| `ALGORITHM` | `HS256` | الگوریتم JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | عمر access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | عمر refresh token |
| `OTP_LENGTH` | `6` | طول کد OTP |
| `OTP_TTL_SECONDS` | `120` | اعتبار کد OTP |
| `OTP_RESEND_COOLDOWN` | `60` | حداقل فاصله بین دو درخواست OTP |
| `OTP_MAX_ATTEMPTS` | `5` | حداکثر تلاش اشتباه |
| `REGISTRATION_TTL_SECONDS` | `600` | مدت نگهداری ثبت‌نام معلق |
| **`S3_ENDPOINT_URL`** | `https://...arvanstorage.ir` | آدرس باکت (از پنل آروان کپی کن) |
| **`S3_ACCESS_KEY`** | — | Access Key آروان |
| **`S3_SECRET_KEY`** | — | Secret Key آروان |
| **`S3_BUCKET`** | — | نام باکت |
| `S3_REGION` | `default` | ریجن (طبق داک آروان `default`) |
| `S3_ADDRESSING_STYLE` | `virtual` | `virtual` یا `path` |
| `S3_PUBLIC_READ` | `false` | `true`=لینک عمومی دائمی، `false`=presigned موقت |
| `MAX_UPLOAD_BYTES` | `209715200` | سقف حجم هر فایل (۲۰۰MB) |
| `BUCKET_QUOTA_BYTES` | `5368709120` | سهمیه‌ی کل باکت (۵GB) |
| `DOWNLOAD_URL_TTL_SECONDS` | `3600` | عمر لینک دانلود موقت |

---

## 🔗 مسیرهای API

### احراز هویت (`/auth`)

| متد | مسیر | توضیح |
|-----|------|-------|
| `POST` | `/auth/register` | شروع ثبت‌نام و ارسال OTP |
| `POST` | `/auth/verify-otp` | تأیید OTP و ساخت کاربر (بازگشت توکن) |
| `POST` | `/auth/resend-otp` | ارسال مجدد OTP |
| `POST` | `/auth/login/phone` | لاگین با موبایل + پسورد |
| `POST` | `/auth/login/username` | لاگین با یوزرنیم + پسورد |
| `POST` | `/auth/token` | لاگین فرم OAuth2 (برای Swagger) |
| `POST` | `/auth/refresh` | تعویض refresh token |
| `POST` | `/auth/logout` | خروج (باطل‌سازی نشست فعلی) |
| `GET`  | `/auth/me` | پروفایل کاربر جاری |
| `PATCH`| `/auth/me` | ویرایش جزئی پروفایل |
| `POST` | `/auth/change-password` | تغییر پسورد |

### فایل‌ها (`/files`) — نیازمند لاگین

| متد | مسیر | توضیح |
|-----|------|-------|
| `POST` | `/files` | آپلود فایل (فرم: `name`, `description`, `file`) |
| `GET`  | `/files` | لیست/سرچ (`?q=`, `?mine=true`, `skip`, `limit`) |
| `GET`  | `/files/storage` | وضعیت باکت (مصرف/سهمیه) |
| `GET`  | `/files/{id}` | جزئیات فایل + لینک دانلود |
| `GET`  | `/files/{id}/download` | ریدایرکت به لینک دانلود |
| `PATCH`| `/files/{id}` | ویرایش (صاحب فایل یا ادمین) |
| `DELETE`| `/files/{id}` | حذف (صاحب فایل یا ادمین) |

### پنل ادمین (`/admin`) — نیازمند کاربر ادمین

| متد | مسیر | توضیح |
|-----|------|-------|
| `GET`  | `/admin` | رابط HTML پنل |
| `GET`  | `/admin/stats` | آمار منابع سیستم |
| `GET`  | `/admin/health` | سلامت سرویس‌ها |
| `GET`  | `/admin/users` | لیست کاربران |
| `POST` | `/admin/users/{id}/ban` | بن کاربر |
| `POST` | `/admin/users/{id}/unban` | آنبن کاربر |
| `POST` | `/admin/users/{id}/toggle-active` | فعال/غیرفعال |
| `GET`  | `/admin/tokens` | نشست‌های فعال |
| `POST` | `/admin/tokens/revoke` | باطل‌سازی یک نشست |
| `POST` | `/admin/users/{id}/revoke-all` | باطل‌سازی همه نشست‌ها |
| `GET`  | `/admin/storage` | وضعیت باکت + چک دسترسی |
| `GET`  | `/admin/files` | لیست/سرچ همه فایل‌ها |
| `PATCH`| `/admin/files/{id}` | ویرایش هر فایل |
| `DELETE`| `/admin/files/{id}` | حذف هر فایل |

---

## 🧪 نمونه‌ی استفاده

```bash
# ۱) ثبت‌نام (کد OTP در لاگ سرور و در حالت DEBUG در پاسخ چاپ می‌شود)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"ali","phone":"09123456789","password":"secret123"}'

# ۲) تأیید OTP → دریافت توکن
curl -X POST http://localhost:8000/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"09123456789","code":"123456"}'

# ۳) آپلود فایل (با توکن)
curl -X POST http://localhost:8000/files \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "name=گزارش سه‌ماهه" \
  -F "description=فایل تستی" \
  -F "file=@/path/to/report.pdf"

# ۴) سرچ فایل‌ها
curl "http://localhost:8000/files?q=گزارش" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# ۵) دانلود (ریدایرکت به لینک باکت)
curl -L "http://localhost:8000/files/1/download" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" -o out.pdf
```

---

## ⚠️ نکات پرودАкشن

- 🔑 `SECRET_KEY` را حتماً عوض کن و **در گیت commit نکن** (`.env` در `.gitignore` است).
- 🗝️ اگر Access/Secret Key آروان جایی لو رفت، از پنل **rotate/باطل** کن.
- 📵 در حالت واقعی فیلد `debug_otp` را حذف کن (`DEBUG=false`) — فقط برای تست است.
- 📨 سرویس واقعی ارسال پیامک (SMS gateway) را جایگزین چاپ OTP در لاگ کن.
- 🗄️ برای بار بالا SQLite را با PostgreSQL/MySQL عوض کن (فقط `DATABASE_URL`).
- 🌐 پشت یک reverse proxy (مثل Nginx) با HTTPS مستقر کن.
- 🧹 برای کنترل مصرف باکت، می‌توانی **Lifecycle** آروان را فعال کنی (حذف خودکار فایل‌های قدیمی).

---

## 📝 لایسنس

منتشرشده تحت لایسنس **MIT**.

<div align="center">
ساخته‌شده با ⚡ FastAPI + ArvanCloud s3
</div>
