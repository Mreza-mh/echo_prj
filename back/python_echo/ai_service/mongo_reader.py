"""
MongoDB Patient Data Reader - خواندن اطلاعات بیمار از مونگو
"""
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()


def get_patient_config(patient_id: str | int) -> dict:
    """دریافت کانفیگ بیمار از مونگو
    
    Args:
        patient_id: می‌تواند user_id (int) یا _id (str) باشد
    """
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://127.0.0.1:27017')
    client = MongoClient(mongo_uri)
    collection = client.echo_pipeline.patient_profiles
    
    # اول سعی می‌کنیم با _id پیدا کنیم (اگر string باشد)
    if isinstance(patient_id, str) and len(patient_id) == 24:
        from bson import ObjectId
        try:
            patient = collection.find_one({'_id': ObjectId(patient_id)})
            if patient:
                client.close()
                patient.pop('_id', None)
                patient.pop('created_at', None)
                patient.pop('updated_at', None)
                return patient
        except Exception:
            pass
    
    # اگر پیدا نشد، با user_id جستجو می‌کنیم
    try:
        user_id_int = int(patient_id)
        patient = collection.find_one({'user_id': user_id_int})
    except (ValueError, TypeError):
        patient = None
    
    client.close()
    
    if not patient:
        raise ValueError(f"بیمار با شناسه {patient_id} در مونگو یافت نشد")
    
    # حذف _id
    patient.pop('_id', None)
    patient.pop('created_at', None)
    patient.pop('updated_at', None)
    
    return patient
