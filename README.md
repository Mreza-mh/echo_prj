# echo_prj

پروژه Echo — سامانه ثبت و پردازش هوشمند اکوکاردیوگرافی (ویدیو → اندازه‌گیری → ریسک ML)، به‌همراه پنل وب، برروکر MQTT برای دستگاه‌های ESP32، و سرویس هوش مصنوعی FAISS برای مسیریابی سوالات.

## 🧩 اجزای پروژه

| بخش | مسیر | تکنولوژی | پورت پیش‌فرض |
|---|---|---|---|
| Backend اصلی | `back/laravel` | Laravel 12 / PHP 8.4 | 8000 |
| MQTT Broker | `mqtt-broker` | Mosquitto (Docker) | 1883 |
| سرویس FAISS AI | `back/faiss` | FastAPI + uvicorn (Python) | 9000 |
| پردازش ویدیو/ML اکو | `back/python_echo` | Python (CLI، نه سرویس دائمی) | - |
| فرانت‌اند | `front` | Angular 20 | 4200 |
| Kong Gateway | `kong-gateway` | Kong + Postgres (Docker) — **فعلاً غیرفعال** | proxy 9098 / admin 9099 / Konga 9338 |
| فرمور دستگاه | `esp32/vital_monitor` | Arduino/ESP32 (جدا آپلود می‌شود، بخشی از این راهنما نیست) | - |

نیازمندی‌های زیرساختی مشترک که **خودِ پروژه نصب نمی‌کند** و باید از قبل روی دستگاه باشند: MySQL و MongoDB (هردو لوکال، داکرایز نشده‌اند).

## ✅ پیش‌نیازها (روی دستگاه جدید نصب کنید)

- **Docker Desktop** (برای MQTT Broker و در صورت فعال‌سازی، Kong)
- **PHP 8.4** + اکستنشن `mongodb` (بسته `jenssegers/mongodb` به آن نیاز دارد) + **Composer**
- **MySQL** (نسخه ۸ به بالا، سرویس در حال اجرا روی `127.0.0.1:3306`)
- **MongoDB** (سرویس در حال اجرا روی `127.0.0.1:27017`)
- **Node.js 18.19+** و npm (برای Angular 20)
- **Python 3.12** (ترجیحاً با pyenv، هم برای FAISS و هم برای python_echo استفاده می‌شود)

## 🚀 راه‌انداز سریع (روش پیشنهادی)

اسکریپت `start.ps1` به‌صورت خودکار MQTT Broker + FAISS + Laravel + MQTT Listener را بالا می‌آورد (پیش‌نیازها مثل `composer install`/`key:generate` را هم خودش چک و نصب می‌کند):

```powershell
.\start.ps1          # بالا آوردن همه سرویس‌ها
.\start.ps1 -Stop    # توقف همه سرویس‌ها
```

فرانت و پردازش ویدیو جدا اجرا می‌شوند (پایین توضیح داده شده).

## 🔧 راه‌اندازی دستی هر بخش

### ۱. MQTT Broker (Mosquitto)
```powershell
docker compose -f mqtt-broker/docker-compose.yml up -d
```
روی `localhost:1883` بالا می‌آید.

### ۲. Kong API Gateway (اختیاری — فعلاً استفاده نمی‌شود)
```powershell
docker compose -f kong-gateway/docker-compose.yml up -d
```
`proxy=9098  admin=9099  Konga=9338`. در `start.ps1` کامنت است؛ فقط اگر لازم شد فعال کنید.

### ۳. سرویس FAISS AI
```powershell
cd back/faiss
python -m pip install -r requirements.txt -i https://pypi.devneeds.ir/simple/
python -m uvicorn faiss_api:app --port 9000
```
> نکته ۱: پوشه‌های `local_model/` (مدل NLP) و `embed_database/` در gitignore هستند و باید جدا روی دستگاه جدید قرار بگیرند (طبق `back/faiss/README.md`).
> نکته ۲ (مهم — بدون `--reload` اجرا کنید): چون Qdrant به‌صورت محلی روی پوشهٔ `embed_database/` فایل قفل می‌گذارد و فقط یک پردازه هم‌زمان می‌تواند آن را باز نگه دارد، پرچم `--reload` باعث یک race condition ذاتی می‌شود — وقتی uvicorn worker قدیم را می‌بندد و نوی جدید را می‌سازد، پردازهٔ جدید قبل از آزاد شدن کامل قفل توسط پردازهٔ قبلی تلاش می‌کند دیتابیس را باز کند و با خطای `RuntimeError: Storage folder ... already accessed by another instance` کرش می‌کند (که باعث خطای 500 در `/api/ai/chat` هم می‌شود، چون Laravel نمی‌تواند به FAISS وصل شود). این مشکل با `--reload-exclude` هم حل نمی‌شود چون خودِ اولین بار ری‌استارت شدنِ reloader باعثش می‌شود، نه تغییر فایل. راه‌حل: سرویس را بدون `--reload` اجرا کنید؛ اگر کد را تغییر دادید، سرویس را دستی (Ctrl+C و دوباره اجرا) ری‌استارت کنید.

### ۴. Laravel Backend
```powershell
cd back/laravel
cp .env.example .env          # اگر .env نبود
php artisan key:generate
composer install --no-interaction --prefer-dist
php artisan migrate
php artisan serve --host=0.0.0.0 --port=8000
```
حتماً در `.env`، اطلاعات دیتابیس MySQL (`DB_*`) و MongoDB (`MONGO_DB_*`) را با تنظیمات دستگاه جدید تطبیق دهید.

### ۵. MQTT Listener (دریافت داده حسگرها از ESP32)
```powershell
cd back/laravel
php artisan mqtt:listen
```
روی تاپیک `devices/+/data` گوش می‌دهد؛ به Laravel و Mosquitto نیاز دارد که از قبل بالا باشند.

### ۶. Python Echo (پردازش ویدیو اکو + پیش‌بینی ML)
سرویس دائمی نیست، به‌صورت CLI به‌ازای هر بیمار اجرا می‌شود:
```powershell
cd back/python_echo
python -m pip install -r requirements.txt
python main.py C:/path/to/patient_folder          # پردازش کامل ویدیو + ML
```
پیش‌نیازها:
- فایل `.env` با کلیدهای `ECHO_MONGO_URI`, `ECHO_MONGO_DB`, `ECHO_MONGO_COLLECTION`, `LARAVEL_PUBLIC_RESULT_PATH`, `ARVAN_AI_API_KEY`, `ARVAN_AI_BASE_URL`, `ARVAN_AI_MODEL` — مقادیر را از دستگاه قبلی/تیم بگیرید (سکرت هستند، در گیت قرار ندهید).
- وزن‌های مدل‌های ML در `pipeline/measurement/weights/` و `pipeline/models/` در gitignore هستند و باید جدا کپی شوند.
- به MongoDB در حال اجرا نیاز دارد.

### ۷. فرانت‌اند (Angular)
```powershell
cd front
npm install
npm start            # ng serve, پیش‌فرض روی http://localhost:4200
```
تنظیمات پراکسی به بک‌اند در `front/proxy.conf.json` است.

## ⚠️ نکات مهم برای انتقال به دستگاه جدید

1. **فایل‌های `.env`** (لاراول و python_echo) در گیت نیستند/سکرت دارند — دستی از دستگاه قبلی منتقل یا با مقادیر جدید پر شوند.
2. **مدل‌های ML** (FAISS `local_model/`, python_echo `pipeline/models/` و `pipeline/measurement/weights/`) در gitignore هستند — جدا کپی/دانلود شوند.
3. **MySQL و MongoDB** باید از قبل نصب و در حال اجرا باشند؛ پروژه آن‌ها را داکرایز نکرده است.
4. ترتیب توصیه‌شده اجرا: MQTT Broker → FAISS → Laravel → MQTT Listener → (Front جدا) → (python_echo per-run).
