# فرم ارزیابی ریسک بیماری‌های قلبی و عروقی

## توضیحات
این فرم برای جمع‌آوری اطلاعات پزشکی بیماران جهت ارزیابی ریسک بیماری‌های قلبی و عروقی طراحی شده است.

## ویژگی‌ها
- ✅ فرم چند مرحله‌ای (Multi-step) با استفاده از Material Stepper
- ✅ اعتبارسنجی کامل برای تمام فیلدها
- ✅ Tooltip برای راهنمایی کاربر
- ✅ تمام فیلدها اختیاری (مدل از Missing Value پشتیبانی می‌کند)
- ✅ طراحی Responsive
- ✅ پشتیبانی از حالت تاریک (Dark Mode)
- ✅ اعتبارسنجی سفارشی (مثلاً فشار خون سیستولیک > دیاستولیک)

## ساختار فرم

### مرحله 1: اطلاعات پایه
- سن (age): 18-120 سال
- جنسیت (gender): مرد=1, زن=2
- قد (height): 100-230 سانتی‌متر
- وزن (weight): 30-250 کیلوگرم

### مرحله 2: فشار خون و متابولیسم
- فشار خون سیستولیک (ap_hi): 60-300 mmHg
- فشار خون دیاستولیک (ap_lo): 40-200 mmHg
- وضعیت کلسترول (cholesterol): 1=نرمال, 2=بالاتر از نرمال, 3=بسیار بالا
- وضعیت قند خون (gluc): 1=نرمال, 2=بالاتر از نرمال, 3=بسیار بالا

### مرحله 3: اطلاعات تخصصی قلبی
- نوع درد قفسه سینه (cp): 0-3
- فشار خون استراحت (trestbps): 60-250 mmHg
- کلسترول خون (chol): 100-600 mg/dL
- قند خون ناشتا (fbs): 0=کمتر از 120, 1=بیشتر از 120
- نتیجه ECG استراحت (restecg): 0-2
- حداکثر ضربان قلب (thalach): 40-220
- آنژین ناشی از ورزش (exang): 0=خیر, 1=بله
- افت ST (oldpeak): 0-6.2
- شیب ST (slope): 0-2
- تعداد رگ‌های اصلی (ca): 0-4
- وضعیت تالاسمی (thal): 0-3

### مرحله 4: سبک زندگی
- مصرف سیگار (smoke): 0=خیر, 1=بله
- مصرف الکل (alco): 0=خیر, 1=بله
- فعالیت بدنی (active): 0=غیرفعال, 1=فعال

## نحوه استفاده

### باز کردن به صورت Modal
```typescript
const dialogRef = this.dialog.open(PatientFormComponent, {
  width: '900px',
  maxWidth: '95vw',
  maxHeight: '90vh',
  data: {
    userId: this.userData?.id
  },
  disableClose: false,
  panelClass: 'patient-form-dialog'
});

dialogRef.afterClosed().subscribe(result => {
  if (result?.success) {
    console.log('Data saved:', result.data);
  }
});
```

### استفاده به صورت Standalone Component
```html
<app-patient-form></app-patient-form>
```

## API Endpoints

### ذخیره/به‌روزرسانی اطلاعات
```
POST /api/patient-profile/store
```

**Request Body:**
```json
{
  "user_id": 1,
  "age": 55,
  "gender": 1,
  "sex": 1,
  "height": 172,
  "weight": 90,
  "ap_hi": 158,
  "ap_lo": 98,
  "cholesterol": 2,
  "gluc": 1,
  "smoke": 0,
  "alco": 0,
  "active": 0,
  "cp": 3,
  "trestbps": 158,
  "chol": 294,
  "fbs": 1,
  "restecg": 0,
  "thalach": 106,
  "exang": 1,
  "oldpeak": 2.8,
  "slope": 1,
  "ca": 2,
  "thal": 3
}
```

**Response:**
```json
{
  "success": true,
  "message": "اطلاعات با موفقیت ذخیره شد",
  "data": { ... }
}
```

### دریافت اطلاعات
```
GET /api/patient-profile/{user_id}
```

**Response:**
```json
{
  "success": true,
  "data": { ... }
}
```

## نکات مهم

1. **تبدیل داده‌ها**: فرم به صورت خودکار مقادیر را به عدد تبدیل می‌کند
2. **Gender/Sex**: این دو فیلد از یک ورودی پر می‌شوند (gender برای Cardiovascular Dataset و sex برای Heart Disease Dataset)
3. **Feature Engineering**: Backend مسئول محاسبه BMI، MAP، Pulse Pressure و سایر فیچرهای مهندسی‌شده است
4. **Missing Values**: تمام فیلدها اختیاری هستند و مدل AI از Missing Value پشتیبانی می‌کند
5. **Validation**: اعتبارسنجی در سمت Frontend و Backend انجام می‌شود

## Dependencies
- @angular/material
- @angular/forms
- @angular/common/http

## Styling
فایل‌های استایل:
- `patient-form.component.scss`: استایل‌های کامپوننت
- `styles.scss`: استایل‌های گلوبال برای مودال
