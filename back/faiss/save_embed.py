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


# تابع تولید خودکار جملات برای گسترش دیتابیس (بدون کلمات نوبت‌دهی)
def generate_expanded_knowledge_base():
    # ۱. لیست پارامترهای بسیار گسترده
    insurances = [
        "تامین اجتماعی", "سلامت", "نیروهای مسلح", "بانک تجارت", "بیمه ایران",
        "دانا", "آتیه سازان", "ساتا", "تکمیلی", "البرز", "کوثر", "پارسیان",
        "پاسارگاد", "بیمه معلم", "بیمه دی", "بیمه ملت"
    ]
    locations = [
        "خیابان هفت تیر", "زنجان", "نزدیک کلینیک", "ساختمان پزشکان", "داخل مطب",
        "چهارراه سعدی", "مرکز شهر", "لوکیشن مطب", "محدوده هفت تیر", "بلوار اصلی"
    ]
    equipments = [
        "دستگاه فیلیپس", "سیستم فازی", "پردازش تصویر", "هوش مصنوعی",
        "اکوکاردیوگرافی", "نمای PLAX", "آنالیز هوشمند", "تکنولوژی اکو",
        "اکو رنگی", "تست داپلر", "الگوریتم تشخیص"
    ]

    kb = []

    # ۲. الگوهای متنوع برای بیمه (رسمی و عامیانه)
    templates_insurance = [
        "آیا شما با بیمه {} طرف قرارداد هستید؟",
        "هزینه اکو با دفترچه {} چقدر میشه؟",
        "ویزیت متخصص با {} چنده؟",
        "بیمه {} رو قبول می‌کنید؟",
        "طرف قرارداد با {} هستید یا نه؟",
        "هزینه ویزیت برای کسی که بیمه {} داره چقدره؟",
        "بیمه های طرف قرارداد شامل {} هم میشه؟",
        "دفترچه {} توی کلینیک شما اعتبار داره؟",
        "تخفیف برای بیمه {} دارید؟"
    ]
    for ins in insurances:
        for temp in templates_insurance:
            kb.append({"category": "insurance", "text": temp.format(ins)})

    # ۳. الگوهای آدرس و تماس (بسیار دقیق)
    templates_contact = [
        "لوکیشن دقیق {} کجاست؟",
        "چطوری میتونم حضوری بیام به {}؟",
        "شماره تماس مستقیم پذیرش در {} چنده؟",
        "آدرس پستی کلینیک در {} رو می‌خواستم.",
        "مسیر دسترسی به {} چطوریه؟",
        "نزدیک‌ترین ایستگاه به {} کدومه؟",
        "ساختمان پزشکان در {} کجای خیابونه؟",
        "مطب دکتر در {} طبقه چنده؟",
        "کلینیک توی محدوده {} هست؟",
        "تلفن گویای مطب در {} رو دارید؟"
    ]
    for loc in locations:
        for temp in templates_contact:
            kb.append({"category": "contact_info", "text": temp.format(loc)})

    # ۴. الگوهای فنی و سیستم فازی (برای بخش تخصصی پروژه AcaRee)
    templates_tech = [
        "دقت {} در تشخیص بیماری قلبی چقدره؟",
        "آیا از {} برای تحلیل ویدیوها استفاده میکنید؟",
        "مدل دقیق {} که دارید چیه؟",
        "نحوه کارکرد {} در کلینیک شما چطوریه؟",
        "آیا سیستم {} خطای کمی داره؟",
        "تکنولوژی {} چقدر در تشخیص موثره؟",
        "تفاوت این مرکز با بقیه در استفاده از {} چیه؟",
        "آیا گزارش‌های {} رو به مریض هم میدید؟",
        "این سیستم {} خودکار عمل میکنه؟"
    ]
    for eq in equipments:
        for temp in templates_tech:
            kb.append({"category": "equipments_and_fuzzy", "text": temp.format(eq)})

    # ۵. بخش قوانین، آمادگی و پشتیبانی (با تغییر ساختار جملات)
    rules_base = [
        "باید ناشتا باشم؟",
        "چه مدارکی بیارم؟",
        "جواب چقدر طول میکشه؟",
        "نوار قلب قدیمی لازمه؟",
        "همراه میتونه بیاد تو؟",
        "هزینه چقدر میشه؟",
        "جواب رو همون موقع میدید؟",
        "قبلش کار خاصی باید کرد؟",
        "مدارک جراحی لازمه؟",
        "ساعت کاری مطب چطوریه؟",
        "پنجشنبه ها باز هستید؟",
        "کلینیک جمعه ها تعطیله؟",
        "میتونم از پزشک سوال بپرسم؟",
        "جواب اکو آنلاین فرستاده میشه؟"
    ]

    # استفاده از ترکیبات مختلف برای Support
    prefixes = ["ببخشید ", "سوال داشتم: ", "آیا ", "", "لطفا بگید ", "میشه راهنمایی کنید "]
    suffixes = [" ممنون.", " مرسی.", "؟", "؟ لطفا جواب بدید.", ""]

    for rb in rules_base:
        for pre in prefixes:
            for suf in suffixes:
                kb.append({"category": "rules_and_support", "text": f"{pre}{rb}{suf}"})

    return kb
# ۱. داده‌های دستی اولیه
knowledge_base = [
    {"category": "insurance", "text": "کلینیک قلب ما با بیمه‌های تامین اجتماعی، سلامت و نیروهای مسلح طرف قرارداد است."},
    {"category": "contact_info", "text": "ادرس مطب ما در شهر زنجان، خیابان هفت تیر واقع شده است."},
    {"category": "contact_info", "text": "ادرس مطب  خیابان هفت تیر است."},
    {"category": "equipments_and_fuzzy",
     "text": "تشخیص بیماری در کلینیک ما با کمک یک سیستم منطق فازی پیشرفته انجام می‌پذیرد."},
    {"category": "rules_and_support",
     "text": "برای لغو یا جابجایی نوبت خود، لطفاً حداقل ۲۴ ساعت قبل با پذیرش تماس بگیرید."}
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

# ۵. بازبینی
records, _ = client.scroll(collection_name=collection_name, limit=5)
for r in records:
    print(f"ID: {r.id} | [{r.payload['category']}] -> {r.payload['sentence_text']}")

client.close()