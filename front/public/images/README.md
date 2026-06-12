# 📸 پوشه تصاویر صفحه لندینگ

این پوشه شامل تمام تصاویر مورد نیاز برای صفحه لندینگ پروژه است.

## 📁 ساختار پوشه‌ها

```
images/
├── hero/
│   ├── doctor.jpg (1200×800px) - دکتر در حال کار با تبلت
│   └── echo-background.jpg (1920×1080px) - تصویر اکو blur شده
│
├── logos/
│   ├── angular.svg - لوگو Angular
│   ├── laravel.svg - لوگو Laravel
│   ├── python.svg - لوگو Python
│   ├── kong.svg - لوگو Kong Gateway
│   ├── mongodb.svg - لوگو MongoDB
│   ├── rabbitmq.svg - لوگو RabbitMQ
│   ├── mysql.svg - لوگو MySQL
│   └── qdrant.svg - لوگو Qdrant
│
├── architecture/
│   ├── system-diagram.png (1600×900px) - نمودار معماری سیستم
│   ├── data-flow.svg - خطوط جریان داده (animated)
│   └── circuit-board.png - پس‌زمینه شبکه‌ای
│
├── steps/ (مراحل CV Pipeline)
│   ├── step1-video.jpg (800×600px) - فریم اولیه ویدیو
│   ├── step2-classify.jpg (800×600px) - نتیجه classification با label A4C
│   ├── step3-scale.jpg (800×600px) - ruler detection با خط قرمز
│   ├── step4-segment.jpg (800×600px) - ماسک segmentation روی تصویر
│   └── step5-measure.jpg (800×600px) - خطوط اندازه‌گیری + اعداد
│
├── models/ (معماری مدل‌های AI)
│   ├── cnn-architecture.png (1000×500px) - نمودار معماری CNN
│   ├── unet-architecture.png (1200×600px) - نمودار U-Net++
│   └── training-graph.png (800×400px) - نمودار آموزش مدل
│
├── ml/ (Machine Learning)
│   ├── feature-flow.png (1000×400px) - نمودار flow feature engineering
│   ├── logistic-regression.jpg (800×600px) - نمودار coefficients
│   └── catboost-importance.jpg (800×600px) - feature importance chart
│
├── fuzzy/ (Fuzzy Logic)
│   ├── membership-functions.png (1200×400px) - نمودار 3 تابع membership
│   ├── fuzzy-output.png (800×600px) - نمودار خروجی fuzzy
│   └── fuzzy-rules.png (1000×300px) - جدول قوانین
│
├── llm/ (LLM Integration)
│   ├── sample-report.png (1000×1400px) - اسکرین‌شات گزارش HTML
│   └── llm-prompt.png (800×300px) - مثال prompt
│
└── panels/ (User Panels)
    ├── patient-panel.png (600×800px) - اسکرینشات پنل بیمار
    ├── secretary-panel.png (600×800px) - اسکرینشات پنل منشی
    └── doctor-panel.png (600×800px) - اسکرینشات پنل پزشک
```

## 🎨 راهنمای تهیه تصاویر

### Hero Section
- **doctor.jpg**: عکس یک دکتر در حال استفاده از تبلت یا لپ‌تاپ، با کیفیت بالا و نورپردازی حرفه‌ای
- **echo-background.jpg**: تصویر اکوکاردیوگرافی که با Gaussian Blur پردازش شده (blur radius: 30-50px)

### Steps (CV Pipeline)
- همه تصاویر باید annotation داشته باشند (خطوط، برچسب‌ها، اعداد)
- **step1**: فریم خام از ویدیو اکو
- **step2**: همان فریم با label classification (مثلاً "A4C: 98.5%") در گوشه
- **step3**: تصویر با ruler detection - خط قرمز روی ruler + عدد "28.6 px/cm"
- **step4**: ماسک segmentation (overlay رنگی شفاف) روی تصویر قلب
- **step5**: خطوط اندازه‌گیری افقی و عمودی + مقادیر (مثلاً "LVIDd: 52.4 mm")

### Models
- نمودارهای معماری شبکه عصبی (می‌توان با کتابخانه‌های visualkeras یا PlotNeuralNet تولید کرد)
- یا نمودارهای دستی با Figma/Photoshop

### ML Charts
- نمودارهای matplotlib با style زیبا
- Feature importance charts
- Confusion matrix (اختیاری)

### Fuzzy Logic
- نمودارهای membership functions (trapezoidal, triangular)
- نمودار output با scikit-fuzzy

### LLM
- اسکرینشات از گزارش HTML تولید شده
- فونت فارسی واضح و خوانا

### Panels
- اسکرینشات واقعی از پنل‌های Angular
- حذف اطلاعات حساس (نام بیماران، شماره تلفن، و غیره)
- تصاویر با رزولوشن بالا

## 🔧 ابزارهای پیشنهادی برای تولید تصاویر

- **Figma**: برای طراحی mockup و نمودارها
- **Photoshop/GIMP**: برای ویرایش و annotation
- **Python Matplotlib/Seaborn**: برای نمودارهای ML
- **draw.io**: برای نمودارهای معماری
- **PlotNeuralNet**: برای نمایش معماری شبکه‌های عصبی
- **Excalidraw**: برای نمودارهای ساده و زیبا

## 📝 نکات مهم

1. تمام تصاویر باید فرمت **JPEG** یا **PNG** باشند
2. برای لوگوها حتماً از **SVG** استفاده کنید (scalable)
3. سایز فایل‌ها را کمتر از **500KB** نگه دارید (با ابزارهای compression)
4. از فونت‌های فارسی مناسب مثل **Vazirmatn** یا **Yekan Bakh** استفاده کنید
5. رنگ‌بندی تصاویر باید با پالت رنگی سایت هماهنگ باشد:
   - Primary: #00f0ff (cyan)
   - Secondary: #7000ff (purple)
   - Accent: #ff007c (pink)
   - Background: #050814 (dark)

## 🚀 نحوه استفاده

بعد از قرار دادن تصاویر در پوشه‌های مربوطه، در فایل HTML به صورت زیر استفاده کنید:

```html
<img src="/images/hero/doctor.jpg" alt="Doctor using tablet" />
```

یا در CSS:

```css
background-image: url('/images/hero/echo-background.jpg');
```

---

**نکته**: این فایل README فقط یک راهنما است. بعد از قرار دادن تصاویر واقعی، می‌توانید این فایل را حذف کنید.
