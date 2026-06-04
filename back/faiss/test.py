# quick_test.py
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

tokenizer = AutoTokenizer.from_pretrained("./local_model")
model = AutoModel.from_pretrained("./local_model")

def get_embedding(text):
    encoded = tokenizer(text, padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        output = model(**encoded)
    mask = encoded['attention_mask'].unsqueeze(-1).expand(output[0].size()).float()
    emb = torch.sum(output[0] * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)
    return F.normalize(emb, p=2, dim=1)[0].cpu().numpy().tolist()

# تست با دو روش
test_sentences = [
    # روش قدیمی - فقط جواب
    "آدرس کلینیک قلب ما در شهر زنجان، خیابان هفت تیر واقع شده است.",
    # روش جدید - سوال + جواب
    "آدرس کلینیک کجاست؟ زنجان خیابان هفت تیر",
    "کلینیک کجاست؟ زنجان هفت تیر",
    "ادرس کجاست؟ زنجان هفت تیر",
]

query = "ادرس کلینیک کجاست"
query_vec = get_embedding(query)

print(f"Query: {query}\n")
for sent in test_sentences:
    vec = get_embedding(sent)
    # cosine similarity
    sim = sum(a*b for a,b in zip(query_vec, vec))
    print(f"score: {sim:.4f} | {sent}")