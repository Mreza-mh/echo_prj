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


def encode_text(text):
    encoded_input = tokenizer(text, padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)
    embedding = mean_pooling(model_output, encoded_input['attention_mask'])
    embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)
    return embedding[0].cpu().numpy().tolist()


@app.post("/route")
def route_request(request: UserRequest):
    """
    مسیریابی هوشمند بر اساس میزان شباهت معنایی با داده‌های کلینیک
    """
    try:
        query_vector = encode_text([request.sentence])

        # جستجوی نزدیک‌ترین رکورد در Qdrant
        search_result = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=1
        )

        # حد آستانه برای تشخیص سوالات عمومی کلینیک (بیمه، آدرس و ...)
        # با توجه به داده‌های شما، امتیاز بالای 0.40 نشان‌دهنده شباهت قوی است
        THRESHOLD = 0.60

        if search_result.points and search_result.points[0].score >= THRESHOLD:
            print("support")
            return {
                "intent": "support",
                "score": search_result.points[0].score,
                "matched_sentence": search_result.points[0].payload.get("sentence_text")
            }
        else:
            print("appointment")
            return {
                "intent": "appointment",
                "score": search_result.points[0].score if search_result.points else 0.0,
                "matched_sentence": None
            }



    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search-faiss")
def search(request: UserRequest):
    # این متد کماکان برای بخش RAG و واکشی تمام جملات مشابه حفظ می‌شود
    threshold = 0.20
    query_vector = encode_text([request.sentence])

    search_result = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=5
    )

    results = []
    for hit in search_result.points:
        if hit.score >= threshold:
            results.append({
                "sentence": hit.payload["sentence_text"],
                "similarity": hit.score
            })

    return {
        "query": request.sentence,
        "matches_found": len(results),
        "results": results
    }


# pip install faiss-cpu -i https://pypi.devneeds.ir/simple/
# pip install sentence-transformers==2.2.2 transformers==4.30.2 -i https://pypi.devneeds.ir/simple/