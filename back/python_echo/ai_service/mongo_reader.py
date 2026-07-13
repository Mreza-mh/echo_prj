"""
MongoDB Patient Data Reader - خواندن اطلاعات بیمار از مونگو
"""
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()


def get_patient_config(patient_id: str | int) -> dict:
    """
    دریافت کانفیگ بیمار از MongoDB (collection: echo_pipeline.patient_profiles)

    ورودی:
        patient_id: user_id 

    خروجی:
        دیکشنری اطلاعات بیمار (بدون _id, created_at, updated_at)

    """
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://127.0.0.1:27017')
    client = MongoClient(mongo_uri)
    collection = client.echo_pipeline.patient_profiles

    # فقط با user_id جستجو می‌کنیم (نه با _id مونگو) — چون نام پوشه‌ی ویدیو هم همین user_id هست
    try:
        user_id_int = int(patient_id)
        patient = collection.find_one({'user_id': user_id_int})
    except (ValueError, TypeError):
        patient = None

    client.close()

    if not patient:
        raise ValueError(f"بیمار با شناسه {patient_id} در مونگو یافت نشد")

    # حذف فیلدهای داخلی مونگو که بقیه‌ی پایپ‌لاین بهشون نیازی نداره
    patient.pop('_id', None)
    patient.pop('created_at', None)
    patient.pop('updated_at', None)
    patient.pop('last_vital_reading_at', None)

    return patient
