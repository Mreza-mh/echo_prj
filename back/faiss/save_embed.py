import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance


# تابع تبدیل خروجی مدل به یک بردار واحد (Mean Pooling) به همراه نرمال‌سازی برداری
def get_embedding(text, tokenizer, model):
    encoded_input = tokenizer(text, padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)

    token_embeddings = model_output[0]
    input_mask_expanded = encoded_input['attention_mask'].unsqueeze(-1).expand(token_embeddings.size()).float()

    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    embedding = sum_embeddings / sum_mask
    normalized_embedding = F.normalize(embedding, p=2, dim=1)

    return normalized_embedding[0].cpu().numpy().tolist()


# تابع تولید دیتاست بهبود یافته با دو دسته‌بندی اصلی: support و appointment
def generate_expanded_knowledge_base():
    kb = []

    # ==================== بخش پشتیبانی (Support) ====================
    # همه سوالات غیر نوبت‌گیری در این بخش قرار می‌گیرند
    
    support_items = [
        # آدرس و تماس - بسیار گسترده با انواع سوالات کاربران
        {"category": "support", "text": "آدرس کلینیک قلب ما در شهر زنجان، خیابان هفت تیر واقع شده است."},
        {"category": "support", "text": "ادرس مطب ما در زنجان، خیابان هفت تیر هست."},  # با املای غلط
        {"category": "support", "text": "لوکیشن کلینیک: شهر زنجان، خیابان هفت تیر."},
        {"category": "support", "text": "مکان کلینیک ما در خیابان هفت تیر زنجان است."},
        {"category": "support", "text": "موقعیت جغرافیایی کلینیک: زنجان، خیابان هفت تیر."},
        {"category": "support", "text": "آدرس دقیق: زنجان، خیابان هفت تیر، جنب داروخانه شبانه روزی."},
        {"category": "support", "text": "کلینیک در زنجان، خیابان هفت تیر قرار دارد."},
        {"category": "support", "text": "آدرس پستی: زنجان، صندوق پستی ۱۳۱۴۵-۳۸۵۷۷."},
        {"category": "support", "text": "ایمیل کلینیک: info@acaree-clinic.ir"},
        {"category": "support", "text": "شماره تماس پذیرش: ۳۳۳۳۳۳۳۶"},
        {"category": "support", "text": "برای تماس با بخش پذیرش با شماره ۳۳۳۳۳۳۳۶ تماس بگیرید."},
        {"category": "support", "text": "تلفن مستقیم پذیرش: ۳۳۳۳۳۳۳۶"},
        {"category": "support", "text": "ساعت کاری کلینیک: شنبه تا چهارشنبه از ۸ صبح تا ۸ شب"},
        {"category": "support", "text": "پنجشنبه‌ها تا ساعت ۲ بعدازظهر باز هستیم."},
        {"category": "support", "text": "جمعه‌ها کلینیک تعطیل است."},
        {"category": "support", "text": "پارکینگ اختصاصی در ساختمان پزشکان موجود است."},
        {"category": "support", "text": "نزدیک‌ترین ایستگاه اتوبوس: ایستگاه هفت تیر"},
        {"category": "support", "text": "دسترسی آسان با تاکسی و اتوبوس به کلینیک."},
        {"category": "support", "text": "آدرس روی نقشه: زنجان، خیابان هفت تیر."},
        {"category": "support", "text": "نحوه دسترسی به کلینیک: با ماشین شخصی یا وسایل نقلیه عمومی."},
        
        # بیمه‌ها - با سوالات واقعی کاربران
        {"category": "support", "text": "کلینیک قلب ما با بیمه‌های تامین اجتماعی، سلامت و نیروهای مسلح طرف قرارداد است."},
        {"category": "support", "text": "آیا با بیمه تامین اجتماعی طرف قرارداد هستید؟"},
        {"category": "support", "text": "بیمه تامین اجتماعی در کلینیک ما پذیرفته می‌شود."},
        {"category": "support", "text": "بیمه سلامت برای اکو و ویزیت متخصص قابل استفاده است."},
        {"category": "support", "text": "بیمه نیروهای مسلح برای تمام خدمات کلینیک معتبر است."},
        {"category": "support", "text": "بیمه بانک تجارت را قبول می‌کنیم."},
        {"category": "support", "text": "بیمه ایران در کلینیک ما اعتبار دارد."},
        {"category": "support", "text": "برای بیماران دارای بیمه تکمیلی تخفیف ویژه داریم."},
        {"category": "support", "text": "بیمه دانا و آتیه سازان پذیرفته می‌شوند."},
        {"category": "support", "text": "لیست کامل بیمه‌های طرف قرارداد: تامین اجتماعی، سلامت، نیروهای مسلح، بانک تجارت، بیمه ایران، دانا، آتیه سازان"},
        {"category": "support", "text": "هزینه اکو با دفترچه تامین اجتماعی ۱۵۰ هزار تومان است."},
        {"category": "support", "text": "ویزیت متخصص با بیمه سلامت رایگان است."},
        {"category": "support", "text": "بیمه دی و ملت هم پذیرفته می‌شوند."},
        {"category": "support", "text": "آیا بیمه ساتا را قبول می‌کنید؟"},
        {"category": "support", "text": "بیمه البرز و کوثر هم معتبر هستند."},
        {"category": "support", "text": "برای بیمه پارسیان تخفیف داریم."},
        {"category": "support", "text": "بیمه پاسارگاد و معلم هم پذیرفته می‌شوند."},
        {"category": "support", "text": "هزینه ویزیت با بیمه تامین اجتماعی چقدر است؟"},
        {"category": "support", "text": "اکو با بیمه نیروهای مسلح چنده؟"},
        {"category": "support", "text": "تخفیف برای بیمه سلامت دارید؟"},
        {"category": "support", "text": "آیا دفترچه بیمه ایران توی کلینیک شما اعتبار داره؟"},
        {"category": "support", "text": "طرف قرارداد با بیمه دی هستید یا نه؟"},
        {"category": "support", "text": "بیمه‌های طرف قرارداد شامل بانک تجارت هم میشه؟"},
        
        # آمادگی قبل از اکو
        {"category": "support", "text": "برای اکوی قلبی باید ناشتا باشید."},
        {"category": "support", "text": "حداقل ۴ ساعت قبل از اکو چیزی نخورید."},
        {"category": "support", "text": "آب می‌توانید بخورید ولی غذا و نوشیدنی‌های دیگر ممنوع است."},
        {"category": "support", "text": "داروهای قلبی خود را طبق دستور پزشک مصرف کنید."},
        {"category": "support", "text": "نوار قلب قدیمی خود را حتماً همراه بیاورید."},
        {"category": "support", "text": "مدارک جراحی قبلی اگر دارید همراه داشته باشید."},
        {"category": "support", "text": "پرونده پزشکی قبلی خود را بیاورید."},
        {"category": "support", "text": "شناسنامه یا کارت ملی برای ثبت اطلاعات لازم است."},
        {"category": "support", "text": "کارت بیمه خود را فراموش نکنید."},
        {"category": "support", "text": "همراه بیمار می‌تواند داخل اتاق اکو بیاید."},
        {"category": "support", "text": "قبل از اکو سیگار نکشید."},
        {"category": "support", "text": "استرس نداشته باشید، اکو یک فرآیند بدون درد است."},
        
        # قوانین لغو و جابجایی
        {"category": "support", "text": "برای لغو نوبت خود حداقل ۲۴ ساعت قبل با پذیرش تماس بگیرید."},
        {"category": "support", "text": "جابجایی نوبت با هماهنگی پذیرش امکان‌پذیر است."},
        {"category": "support", "text": "در صورت عدم حضور در زمان مقرر، نوبت شما لغو می‌شود."},
        {"category": "support", "text": "برای بیماران اورژانسی نوبت‌دهی فوری داریم."},
        {"category": "support", "text": "تأخیر بیش از ۱۵ دقیقه باعث لغو نوبت می‌شود."},
        {"category": "support", "text": "برای لغو تلفنی با شماره ۳۳۳۳۳۳۳۶ تماس بگیرید."},
        {"category": "support", "text": "لغو نوبت از طریق وبسایت هم امکان‌پذیر است."},
        {"category": "support", "text": "در صورت بیماری اورژانسی با ما تماس بگیرید."},
        
        # تجهیزات و فناوری‌ها
        {"category": "support", "text": "تشخیص بیماری در کلینیک ما با کمک یک سیستم منطق فازی پیشرفته انجام می‌پذیرد."},
        {"category": "support", "text": "دستگاه اکوی فیلیپس پیشرفته در کلینیک ما موجود است."},
        {"category": "support", "text": "سیستم پردازش تصویر هوشمند برای تحلیل اکو داریم."},
        {"category": "support", "text": "از هوش مصنوعی برای تشخیص دقیق‌تر بیماری‌های قلبی استفاده می‌کنیم."},
        {"category": "support", "text": "اکوکاردیوگرافی رنگی با کیفیت بالا انجام می‌دهیم."},
        {"category": "support", "text": "تست داپلر برای بررسی جریان خون داریم."},
        {"category": "support", "text": "الگوریتم‌های تشخیص خودکار برای تحلیل نتایج اکو داریم."},
        {"category": "support", "text": "نمای PLAX برای تصویربرداری دقیق قلبی استفاده می‌شود."},
        {"category": "support", "text": "تکنولوژی اکوی پیشرفته با کمترین خطا"},
        {"category": "support", "text": "سیستم آنالیز هوشمند ویدیوهای اکو"},
        
        # هزینه‌ها و پرداخت
        {"category": "support", "text": "هزینه اکوی قلبی ۵۰۰ هزار تومان است."},
        {"category": "support", "text": "ویزیت متخصص قلب ۲۵۰ هزار تومان هزینه دارد."},
        {"category": "support", "text": "برای بیماران دارای بیمه تخفیف ویژه داریم."},
        {"category": "support", "text": "پرداخت نقدی، کارت‌خوان و آنلاین پذیرفته می‌شود."},
        {"category": "support", "text": "هزینه نوار قلب ۱۰۰ هزار تومان است."},
        {"category": "support", "text": "هولتر مانیتورینگ ۸۰۰ هزار تومان هزینه دارد."},
        {"category": "support", "text": "تست ورزش ۴۰۰ هزار تومان است."},
        {"category": "support", "text": "لیست کامل تعرفه‌ها در پذیرش موجود است."},
        {"category": "support", "text": "برای خانواده‌های پرجمعیت تخفیف داریم."},
        {"category": "support", "text": "هزینه‌ها با بیمه به صورت توافقی محاسبه می‌شود."},
    
        
        # خدمات کلینیک
        {"category": "support", "text": "اکوکاردیوگرافی معمولی و رنگی"},
        {"category": "support", "text": "نوار قلب معمولی و ورزشی"},
        {"category": "support", "text": "هولتر مانیتورینگ ۲۴ ساعته"},
        {"category": "support", "text": "تست ورزش قلبی"},
        {"category": "support", "text": "اکو قلب جنین"},
        {"category": "support", "text": "اکو قلب کودکان"},
        {"category": "support", "text": "اکو قلب سالمندان"},
        {"category": "support", "text": "ویزیت متخصص قلب"},
        {"category": "support", "text": "چکاپ کامل قلبی"},
        {"category": "support", "text": "مشاوره بیماری‌های قلبی"},
        {"category": "support", "text": "درمان فشار خون بالا"},
        {"category": "support", "text": "درمان آریتمی قلبی"},
        {"category": "support", "text": "بررسی نارسایی قلبی"},
        {"category": "support", "text": "بررسی درد قفسه سینه"},
        
        # سوالات عمومی پشتیبانی
        {"category": "support", "text": "جواب اکو چقدر طول می‌کشد؟"},
        {"category": "support", "text": "جواب آزمایش را همون روز می‌دهید؟"},
        {"category": "support", "text": "آیا جواب آنلاین می‌فرستید؟"},
        {"category": "support", "text": "چطور جواب را دریافت کنم؟"},
        {"category": "support", "text": "می‌توانم از پزشک سوال بپرسم؟"},
        {"category": "support", "text": "آیا همراه می‌تواند داخل بیاید؟"},
        {"category": "support", "text": "پارکینگ دارید؟"},
        {"category": "support", "text": "آسانسور برای سالمندان دارید؟"},
        {"category": "support", "text": "آیا صندلی چرخدار دارید؟"},
        {"category": "support", "text": "دسترسی برای معلولین چطور است؟"},
        {"category": "support", "text": "آیا ویلچر در اختیار می‌گذارید؟"},
        {"category": "support", "text": "آبخوری و سرویس بهداشتی کجاست؟"},
        {"category": "support", "text": "آیا پذیرش ۲۴ ساعته دارید؟"},
        {"category": "support", "text": "آیا جمعه‌ها باز هستید؟"},
        {"category": "support", "text": "آیا تعطیلات رسمی باز هستید؟"},
        {"category": "support", "text": "آیا شب‌ها هم اکو انجام می‌دهید؟"},
        {"category": "support", "text": "برای اورژانس چه کاری باید کرد؟"},
        {"category": "support", "text": "آیا آمبولانس دارید؟"},
        {"category": "support", "text": "با اورژانس ۱۱۵ هماهنگی دارید؟"},
    ]

    # ==================== بخش نوبت‌گیری (Appointment) ====================
    
    # سوالات رایج نوبت‌گیری - به صورت طبیعی و کاربردی
    appointment_items = [
        {"category": "appointment", "text": "چطور می‌توانم نوبت بگیرم؟"},
        {"category": "appointment", "text": "نوبت اکوی قلبی چطور رزرو کنم؟"},
        {"category": "appointment", "text": "می‌خواهم نوبت دکتر قلب بگیرم."},
        {"category": "appointment", "text": "نوبت‌دهی آنلاین دارید؟"},
        {"category": "appointment", "text": "چطور می‌توانم نوبت آنلاین بگیرم؟"},
        {"category": "appointment", "text": "نوبت حضوری می‌خواهم."},
        {"category": "appointment", "text": "آیا می‌توانم امروز نوبت بگیرم؟"},
        {"category": "appointment", "text": "فردا نوبت خالی دارید؟"},
        {"category": "appointment", "text": "برای شنبه نوبت می‌خواهم."},
        {"category": "appointment", "text": "نوبت اورژانسی می‌خواهم."},
        {"category": "appointment", "text": "دکتر متخصص قلب برای نوبت می‌خواهم."},
        {"category": "appointment", "text": "نوبت اکو می‌خواهم."},
        {"category": "appointment", "text": "نوبت ویزیت متخصص قلب"},
        {"category": "appointment", "text": "می‌خواهم برای تست ورزش نوبت بگیرم."},
        {"category": "appointment", "text": "نوبت هولتر مانیتورینگ می‌خواهم."},
        {"category": "appointment", "text": "نوبت اکوکاردیوگرافی"},
        {"category": "appointment", "text": "نوبت اکو رنگی می‌خواهم."},
        {"category": "appointment", "text": "نوبت تست داپلر"},
        {"category": "appointment", "text": "برای بررسی قلب نوزاد نوبت می‌خواهم."},
        {"category": "appointment", "text": "نوبت چکاپ قلب می‌خواهم."},
        # سوالات طبیعی‌تر کاربران
        {"category": "appointment", "text": "ببخشید می‌خوام برای اکوی قلبی وقت بگیرم."},
        {"category": "appointment", "text": "لطفا یک نوبت برای دکتر احمدی بذارید."},
        {"category": "appointment", "text": "نوبت دکتر متخصص قلب می‌خوام."},
        {"category": "appointment", "text": "می‌تونم برای فردا نوبت اکو بگیرم؟"},
        {"category": "appointment", "text": "آیا دکتر محمدی وقت خالی دارن؟"},
        {"category": "appointment", "text": "برای اکو قلبی نیاز به نوبت دارم."},
        {"category": "appointment", "text": "نوبت ویزیت قلب می‌خوام."},
        {"category": "appointment", "text": "می‌شه برای تست ورزش قلب وقت بدید؟"},
        {"category": "appointment", "text": "نوبت اورژانس قلب می‌خوام."},
        {"category": "appointment", "text": "باید برای اکو نوبت بگیرم."},
        {"category": "appointment", "text": "لطفا نوبت اکوکاردیوگرافی بدید."},
        {"category": "appointment", "text": "نوبت دکتر کریمی برای اکوی کودکان می‌خوام."},
        {"category": "appointment", "text": "برای بررسی قلب نوزادم وقت نیاز دارم."},
        {"category": "appointment", "text": "نوبت دکتر رضایی برای اکوی رنگی می‌خوام."},
        {"category": "appointment", "text": "می‌تونم برای همین هفته نوبت بگیرم؟"},
        {"category": "appointment", "text": "آیا امکان رزرو نوبت تلفنی وجود داره؟"},
        {"category": "appointment", "text": "نوبت چکاپ کامل قلب می‌خوام."},
        {"category": "appointment", "text": "برای ویزیت قلب دکتر احمدی وقت می‌خوام."},
        {"category": "appointment", "text": "نوبت تست داپلر قلبی می‌خوام."},
        {"category": "appointment", "text": "لطفا برای هولتر مان��تورینگ وقت بذارید."},
    ]

    # ترکیب همه آیتم‌ها
    all_items = support_items + appointment_items
    
    return all_items


# ۱. داده‌های دستی اولیه (به‌روزرسانی شده)
knowledge_base = [
    # اطلاعات اصلی پشتیبانی
    {"category": "support", "text": "کلینیک قلب ما با بیمه‌های تامین اجتماعی، سلامت و نیروهای مسلح طرف قرارداد است."},
    {"category": "support", "text": "آدرس کلینیک ما در شهر زنجان، خیابان هفت تیر واقع شده است."},
    {"category": "support", "text": "شماره تماس پذیرش: ۳۳۳۳۳۳۳۶"},
    {"category": "support", "text": "تشخیص بیماری در کلینیک ما با کمک یک سیستم منطق فازی پیشرفته انجام می‌پذیرد."},
    {"category": "support", "text": "برای لغو یا جابجایی نوبت خود، لطفاً حداقل ۲۴ ساعت قبل با پذیرش تماس بگیرید."},
    {"category": "support", "text": "برای اکوی قلبی باید ناشتا باشید و حداقل ۴ ساعت قبل چیزی نخورید."},
    {"category": "support", "text": "هزینه اکوی قلبی ۵۰۰ هزار تومان است و برای بیمه‌ها تخفیف ویژه داریم."},
    {"category": "support", "text": "پزشکان کلینیک: دکتر احمدی متخصص قلب، دکتر محمدی فوق تخصص اکو، دکتر رضایی متخصص اکوی رنگی"},
    {"category": "support", "text": "خدمات کلینیک: اکوکاردیوگرافی، نوار قلب، هولتر مانیتورینگ، تست ورزش، ویزیت متخصص"},
    
    # اطلاعات اضافی برای پوشش بهتر
    {"category": "support", "text": "ادرس مطب ما در زنجان، خیابان هفت تیر هست."},  # با املای غلط
    {"category": "support", "text": "لوکیشن کلینیک در شهر زنجان، خیابان هفت تیر است."},
    {"category": "support", "text": "مکان کلینیک: زنجان، خیابان هفت تیر."},
    {"category": "support", "text": "آدرس دقیق کلینیک قلب در زنجان، خیابان هفت تیر."},
    {"category": "support", "text": "کلینیک در خیابان هفت تیر زنجان واقع شده."},
    
    # اطلاعات نوبت‌گیری
    {"category": "appointment", "text": "برای گرفتن نوبت می‌توانید به صورت آنلاین از طریق وبسایت یا با شماره ۳۳۳۳۳۳۳۶ تماس بگیرید."},
    {"category": "appointment", "text": "نوبت اکوی قلبی از طریق تماس تلفنی یا وبسایت امکان‌پذیر است."},
    {"category": "appointment", "text": "برای رزرو نوبت دکتر قلب با پذیرش تماس بگیرید."},
    
    # اطلاعات عمومی
    {"category": "support", "text": "جواب اکو در همان روز آماده می‌شود و می‌توانید به صورت آنلاین دریافت کنید."},
    {"category": "support", "text": "ساعت کاری: شنبه تا چهارشنبه ۸ صبح تا ۸ شب، پنجشنبه‌ها تا ۲ بعدازظهر."},
    {"category": "support", "text": "جمعه‌ها کلینیک تعطیل است."},
    {"category": "support", "text": "پارکینگ اختصاصی برای بیماران وجود دارد."},
]

# ۲. لود کردن مدل
print("در حال لود کردن مدل...")
tokenizer = AutoTokenizer.from_pretrained("./local_model")
model = AutoModel.from_pretrained("./local_model")
vector_size = model.config.hidden_size

# ۳. اتصال به Qdrant
client = QdrantClient(path="./embed_database")
collection_name = "embeds"
if client.collection_exists(collection_name):
    client.delete_collection(collection_name)

client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
)

# ۴. ترکیب داده‌ها و ذخیره‌سازی
print("در حال تولید دیتاست گسترده و امبدینگ‌ها...")
auto_kb = generate_expanded_knowledge_base()
final_kb = knowledge_base + auto_kb  # ترکیب لیست دستی و خودکار

points = []
for i, item in enumerate(final_kb):
    vector = get_embedding(item["text"], tokenizer, model)
    points.append(PointStruct(
        id=i + 1,
        vector=vector,
        payload={"sentence_text": item["text"], "category": item["category"]}
    ))

client.upsert(collection_name=collection_name, points=points)
print(f"✅ تعداد {len(final_kb)} جمله با موفقیت ذخیره شد.")

# ۵. بازبینی و نمایش نمونه‌ها از هر دسته‌بندی
print("\n📊 نمونه‌هایی از هر دسته‌بندی:")
records, _ = client.scroll(collection_name=collection_name, limit=20)
categories_seen = set()

for r in records:
    category = r.payload['category']
    if category not in categories_seen:
        categories_seen.add(category)
        print(f"\n[{category.upper()}]:")
    print(f"  • {r.payload['sentence_text']}")

# ۶. آمار دسته‌بندی‌ها
print(f"\n📈 آمار دیتاست:")
print(f"• کل جملات: {len(final_kb)}")
category_counts = {}
for item in final_kb:
    category_counts[item['category']] = category_counts.get(item['category'], 0) + 1

for category, count in sorted(category_counts.items()):
    print(f"• {category}: {count} جمله")

client.close()
print("\n🎉 دیتاست با موفقیت بهبود یافت و ذخیره شد!")