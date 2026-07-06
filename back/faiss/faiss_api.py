import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModel
import torch
from qdrant_client import QdrantClient

app = FastAPI()

print("در حال لود کردن مدل...")
tokenizer = AutoTokenizer.from_pretrained("./local_model")
model = AutoModel.from_pretrained("./local_model")

print("در حال اتصال به دیتابیس Qdrant...")
client = QdrantClient(path="./embed_database")
collection_name = "embeds"


class UserRequest(BaseModel):
    sentence: str


def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


def encode_text(text: str) -> list:
    # text باید رشته باشه، نه لیست
    encoded_input = tokenizer(text, padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)
    embedding = mean_pooling(model_output, encoded_input['attention_mask'])
    embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)
    return embedding[0].cpu().numpy().tolist()

APPOINTMENT_KEYWORDS = [
    "نوبت بگیر", "رزرو کن", "وقت بگیر", "تایم بگیر", "برنامه ریز", "نوبت دهی", "نوبت گیری",
    "نوبت میخوام", "نوبت می‌خوام", "وقت میخوام", "وقت می‌خوام", "رزرو نوبت", "نوبت خالی",
    "میخوام نوبت", "می‌خوام نوبت", "ویزیت میخوام", "ویزیت می‌خوام",
]
SUPPORT_KEYWORDS = [
    "آدرس", "ادرس", "کجا", "لوکیشن", "مکان", "محل", "تلفن", "شماره", "بیمه", "هزینه", "قیمت",
    "تعرفه", "ساعت کاری", "ساعت کار", "چند تومان", "چقدر می‌گیرید", "چقدر میگیرید",
    "کلینیک کجاست", "مطب کجاست", "درمانگاه", "چه بیمه", "کدوم بیمه", "کدام بیمه",
    "باز هستید", "باز است", "تعطیل", "پارکینگ", "چطور بیایم", "مسیر",
]

# ۳. مهم‌ترین اصلاح: اولویت کلمات کلیدی را بالاتر ببرید
@app.post("/route")
def route_request(request: UserRequest):
    try:
        user_text = request.sentence

        has_support_keyword = any(keyword in user_text for keyword in SUPPORT_KEYWORDS)
        has_appointment_keyword = any(keyword in user_text for keyword in APPOINTMENT_KEYWORDS)

        # ۳. پردازش برداری
        query_vector = encode_text(request.sentence)
        search_result = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=5
        )

        if not search_result.points:
            intent = "support" if has_support_keyword else "appointment"
            return {"intent": intent, "score": 0.0, "reason": "no vector results"}

        top_score = search_result.points[0].score
        top_category = search_result.points[0].payload.get("category", "unknown")
        
        # ۴. منطق تصمیم‌گیری نهایی (Priority Logic)
        # اولویت ۱: کلمات کلیدی صریح (اگر فقط یکی از دو نوع باشد)
        if has_support_keyword and not has_appointment_keyword:
            intent, reason = "support", "explicit support keyword"
        elif has_appointment_keyword and not has_support_keyword:
            intent, reason = "appointment", "explicit appointment keyword"
        
        # اولویت ۲: استفاده از امتیاز برداری (اگر کلمات کلیدی مبهم بودند یا وجود نداشتند)
        else:
            THRESHOLD = 0.45 
            if top_score >= THRESHOLD:
                intent = top_category
                reason = "high vector score"
            else:
                # اگر امتیاز پایین بود، به نفع "appointment" (رزرو نوبت) رای بده (طبق نیاز سیستم شما)
                intent = "appointment"
                reason = "low score fallback"

        print(f"Final Decision -> Intent: {intent} (Score: {top_score:.3f}, Reason: {reason})")
        
        return {
            "intent": intent,
            "score": top_score,
            "matched_sentence": search_result.points[0].payload.get("sentence_text"),
            "category": top_category,
            "reason": reason
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
DIRECT_ANSWERS = {
    ("آدرس", "ادرس", "کجا", "لوکیشن", "مکان", "محل", "درمانگاه", "مسیر"):
        "آدرس کلینیک: زنجان، خیابان هفت تیر",
    ("ساعت", "کاری", "باز", "تعطیل", "وقت کاری"): 
        "شنبه تا چهارشنبه ۸ صبح تا ۸ شب، پنجشنبه تا ۲ بعدازظهر، جمعه تعطیل",
    ("تلفن", "شماره", "تماس"):
        "شماره پذیرش: ۳۳۳۳۳۳۳۶",
    ("بیمه",):
        "بیمه‌های طرف قرارداد: تامین اجتماعی، سلامت، نیروهای مسلح، بانک تجارت، بیمه ایران",
}

@app.post("/search-faiss")
def search(request: UserRequest):
    # اول keyword check
    for keywords, answer in DIRECT_ANSWERS.items():
        if any(kw in request.sentence for kw in keywords):
            return {
                "query": request.sentence,
                "matches_found": 1,
                "results": [{"sentence": answer, "similarity": 1.0}],
                "threshold_used": 0
            }
    
    # بعد vector search
    threshold = 0.50
    query_vector = encode_text(request.sentence)

    search_result = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=10  # افزایش limit برای بازیابی بیشتر
    )

    results = []
    seen_sentences = set()  # برای جلوگیری از تکرار جملات
    
    # اولویت‌بندی: جملات با امتیاز بالا
    for hit in search_result.points:
        if hit.score >= threshold:
            sentence = hit.payload["sentence_text"]
            if sentence not in seen_sentences:
                seen_sentences.add(sentence)
                results.append({
                    "sentence": sentence,
                    "similarity": hit.score
                })
    
    # اگر نتایج کم بود، آستانه را کاهش بده
    if len(results) < 3 and threshold > 0.15:
        threshold = 0.15
        for hit in search_result.points:
            if 0.15 <= hit.score < 0.20:
                sentence = hit.payload["sentence_text"]
                if sentence not in seen_sentences:
                    seen_sentences.add(sentence)
                    results.append({
                        "sentence": sentence,
                        "similarity": hit.score
                    })
    
    # مرتب‌سازی بر اساس شباهت (بالاترین اول)
    results.sort(key=lambda x: x["similarity"], reverse=True)
    
    # محدود کردن به 7 نتیجه
    results = results[:7]
    
    return {
        "query": request.sentence,
        "matches_found": len(results),
        "results": results,
        "threshold_used": threshold
    }


# pip install faiss-cpu -i https://pypi.devneeds.ir/simple/
# pip install sentence-transformers==2.2.2 transformers==4.30.2 -i https://pypi.devneeds.ir/simple/