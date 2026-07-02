
from __future__ import annotations

from pathlib import Path

# ==============================================================================
# مسیرها
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
RESULT_DIR = BASE_DIR / "result"                                                          # ریشه‌ی خروجی همه‌ی پردازش‌ها
CLASSIFIER_MODEL = BASE_DIR / "pipeline" / "models" / "mymodel_echocv_500-500-8_adam_16_0.9394.h5"  # مدل طبقه‌بندی ویو

# ==============================================================================
# ثابت‌های پیش‌فرض پردازش ویدیو
# ==============================================================================

MODEL_VIDEO_SIZE = (640, 480)          # سایز ورودی مورد انتظار مدل طبقه‌بندی ویو
DEFAULT_PIXELS_PER_CM = 12.0           # وقتی تشخیص خودکار مقیاس (scale) شکست بخوره از این مقدار fallback استفاده می‌شه
DEFAULT_ONE_FRAME_REPEAT = 8           # تعداد تکرار فریم تکی برای ساخت ویدیوی یک‌فریمی
DEFAULT_ONE_FRAME_FPS = 10             # fps ویدیوی یک‌فریمی ساخته‌شده

SUPPORTED_CLASSIFIER_LABELS = frozenset(
    {"plax", "psax-av", "psax-mv", "psax-ap", "a2c", "a3c", "a4c", "a5c"}
)

# ==============================================================================
# نقشه‌ی هر ویو به رویدادهای قلبی و مدل‌های اندازه‌گیری مربوطه
# processing.process_video از این دیکشنری می‌خونه تا بفهمه بعد از تشخیص ویو،
# دنبال کدوم رویدادها (events) بگرده و برای هر رویداد کدوم مدل‌های YOLO (event_models) رو اجرا کنه
# اگه ویویی این‌جا نباشه، در process_video به‌عنوان "unsupported_view" علامت می‌خوره
# ==============================================================================

VIEW_PIPELINES: dict[str, dict[str, dict | list[str]]] = {
    "plax": {
        "events": ["End Diastol", "End Sistol", "LVOT"],
        "event_models": {
            # در پایان دیاستول، ضخامت دیواره‌ها و قطر داخلی بطن چپ اندازه‌گیری می‌شود
            "End Diastol": ["ivs", "lvid", "lvpw"],
            # در پایان سیستول، قطر سیستولی بطن چپ و قطر دهلیز چپ (LA) ارزیابی می‌شود
            "End Sistol": ["lvid", "la"],
            # در نمای خروجی بطن چپ، ریشه و دیواره آئورت بررسی می‌شود
            "LVOT": ["aorta", "aortic_root"],
        },
    },
    "psax-av": {
        "events": ["End Sistol"],
        "event_models": {
            # شریان ریوی (PA) و دهلیز چپ (LA) در این نما بهترین دید را دارند
            "End Sistol": ["la", "pa"],
        },
    },
    "psax-mv": {
        "events": [],
        "event_models": {},
    },
    "psax-ap": {
        "events": [],
        "event_models": {},
    },
    "a4c": {
        "events": ["End Diastol", "End Sistol"],
        "event_models": {
            # اندازه پایه بطن راست (RV Base) در پایان دیاستول (بزرگ‌ترین حالت) سنجیده می‌شود
            "End Diastol": ["rv_base"],
            # حجم دهلیز چپ (LA Volume) در پایان سیستول (قبل از باز شدن دریچه میترال) محاسبه می‌شود
            "End Sistol": ["la"],
        },
    },
    "a2c": {
        "events": ["End Sistol"],
        "event_models": {
            # برای محاسبه حجم دهلیز چپ به روش Biplane، نمای دو حفره‌ای هم در پایان سیستول نیاز است
            "End Sistol": ["la"],
        },
    },
    "a3c": {
        "events": ["LVOT"],
        "event_models": {
            # نمای سه حفره‌ای مسیر خروجی بطن چپ و آئورت را به خوبی نشان می‌دهد
            "LVOT": ["aorta", "aortic_root"],
        },
    },
    "a5c": {
        "events": ["LVOT"],
        "event_models": {
            "LVOT": ["aorta"],
        },
    },
}
