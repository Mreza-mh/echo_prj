# سرویس FAISS AI - سیستم مسیریابی هوشمند

## 📋 معرفی
این سرویس برای مسیریابی هوشمند سوالات کاربران بر اساس شباهت معنایی با داده‌های کلینیک طراحی شده است. از مدل‌های Sentence-BERT برای تولید embedding و Qdrant برای جستجوی برداری استفاده می‌کند.

## 🚀 راه‌اندازی سریع

### 1. نصب وابستگی‌ها
```bash
# روش 1: استفاده از اسکریپت (ویندوز)
install_deps.bat

# روش 2: دستی
pip install -r requirements.txt -i https://pypi.devneeds.ir/simple/
```

### 2. اجرای سرویس
```bash
uvicorn faiss_api:app --host 0.0.0.0 --port 8000 --reload
```

سرویس روی آدرس `http://localhost:8000` در دسترس خواهد بود.

## 📁 ساختار پروژه

```
faiss/
├── faiss_api.py          # سرور اصلی FastAPI
├── save_embed.py         # اسکریپت ذخیره‌سازی embedding
├── requirements.txt      # لیست وابستگی‌ها
├── install_deps.bat      # اسکریپت نصب (ویندوز)
├── local_model/          # مدل‌های NLP (در gitignore)
│   ├── .gitkeep         # برای حفظ ساختار پوشه
│   ├── config.json
│   ├── model.safetensors
│   └── ...
├── embed_database/       # پایگاه داده Qdrant (در gitignore)
│   ├── .gitkeep         # برای حفظ ساختار پوشه
│   └── collection/
└── __pycache__/         # فایل‌های کش پایتون
```

## 🔧 API Endpoints

### 1. مسیریابی هوشمند
```
POST /route
```

**ورودی:**
```json
{
  "sentence": "آدرس کلینیک شما کجاست؟"
}
```

**خروجی:**
```json
{
  "intent": "support",
  "score": 0.85,
  "matched_sentence": "ادرس مطب ما در شهر زنجان، خیابان هفت تیر واقع شده است."
}
```

### 2. جستجوی مشابه‌ها
```
POST /search-faiss
```

**ورودی:** مشابه endpoint بالا

**خروجی:** لیست 5 جمله مشابه با امتیاز similarity

## 🛠️ توسعه

### ذخیره‌سازی داده‌های جدید
```bash
python save_embed.py
```

این اسکریپت:
1. مدل را لود می‌کند
2. دیتابیس Qdrant را راه‌اندازی می‌کند  
3. داده‌های موجود را به embedding تبدیل می‌کند
4. در پایگاه داده ذخیره می‌کند

### تنظیم آستانه‌ها
- `FAISS_ROUTE_THRESHOLD`: آستانه تشخیص intent (پیش‌فرض: 0.60)
- `FAISS_SEARCH_THRESHOLD`: آستانه جستجوی مشابه‌ها (پیش‌فرض: 0.20)

## ⚠️ نکات مهم

1. **مدل‌ها در gitignore هستند** - فایل‌های مدل با حجم بالا در گیت ذخیره نمی‌شوند
2. **نیاز به دانلود مدل** - قبل از اولین اجرا، مدل باید در `local_model/` قرار گیرد
3. **پورت 8000** - مطمئن شوید پورت 8000 آزاد است
4. **حافظه** - مدل‌ها به حدود 2GB RAM نیاز دارند

## 🔗 مستندات

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Sentence Transformers](https://www.sbert.net/)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/)