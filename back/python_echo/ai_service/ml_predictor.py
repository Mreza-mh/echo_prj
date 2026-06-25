from __future__ import annotations

import json
import math
import os
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np

# ─── Model file paths ────────────────────────────────────────────────────────
MODELS_DIR = Path(
    os.getenv("CARDIOAI_MODELS_DIR",
                Path(__file__).resolve().parent / "models")
)

# ─── Feature lists — exact order used during training ─────────────────────────
HD_FEATURES_DEFAULT: List[str] = [
    # Raw features (Heart Disease dataset)
    "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
    "thalach", "exang", "oldpeak", "slope", "ca", "thal",
    # Engineered features (Cell 5 notebook)
    "bp_category", "rate_pressure_product", "chronotropic_index",
    "st_depression_index", "age_st_depression",
]

CV_FEATURES_DEFAULT: List[str] = [
    # Raw features (Cardiovascular dataset)
    "age", "gender", "height", "weight",
    "ap_hi", "ap_lo", "cholesterol", "gluc", "smoke", "alco", "active",
    # Engineered features (Cell 5 notebook)
    "bmi", "bmi_category", "map", "pulse_pressure", "hypertension_grade",
    "metabolic_risk_score", "lifestyle_risk_score",
    "age_bmi_interaction", "age_hypertension_interaction",
]

# ─── Clinical population medians — fallback imputation ────────────────────────
CLINICAL_MEDIANS: Dict[str, float] = {
    # HD
    "age": 54.0, "sex": 1.0, "cp": 0.0, "trestbps": 130.0,
    "chol": 240.0, "fbs": 0.0, "restecg": 0.0, "thalach": 149.0,
    "exang": 0.0, "oldpeak": 0.8, "slope": 1.0, "ca": 0.0, "thal": 2.0,
    "bp_category": 1.0, "rate_pressure_product": 193.7,
    "chronotropic_index": 0.916, "st_depression_index": 0.54,
    "age_st_depression": 43.2,
    # CV
    "gender": 1.0, "height": 165.0, "weight": 72.0,
    "ap_hi": 120.0, "ap_lo": 80.0, "cholesterol": 1.0, "gluc": 1.0,
    "smoke": 0.0, "alco": 0.0, "active": 1.0,
    "bmi": 26.5, "bmi_category": 1.0, "map": 93.3,
    "pulse_pressure": 40.0, "hypertension_grade": 0.0,
    "metabolic_risk_score": 0.0, "lifestyle_risk_score": -1.5,
    "age_bmi_interaction": 14.3, "age_hypertension_interaction": 0.0,
}

# ─── Risk factor definitions ────────────────────────────────────────────────
#     (rule, label_fa, label_en)
RISK_FACTOR_DEFS: Dict[str, Tuple] = {
    "age":               (lambda v: v > 65,   "سن بالا (بیش از ۶۵ سال)",               "Age > 65 years"),
    "trestbps":          (lambda v: v > 140,  "فشار خون استراحت بالا (>140 mmHg)",    "Resting BP > 140 mmHg"),
    "ap_hi":             (lambda v: v > 140,  "فشار سیستولی بالا (>140 mmHg)",        "Systolic BP > 140 mmHg"),
    "chol":              (lambda v: v > 240,  "کلسترول بالا (>240 mg/dL)",            "Cholesterol > 240 mg/dL"),
    "fbs":               (lambda v: v == 1,   "قند خون ناشتا بالا (>120 mg/dL)",     "Fasting blood sugar > 120"),
    "exang":             (lambda v: v == 1,   "آنژین ناشی از ورزش",                   "Exercise-induced angina"),
    "oldpeak":           (lambda v: v > 2.0,  "افسردگی ST در ECG (>2 mm)",            "ST depression > 2 mm"),
    "smoke":             (lambda v: v == 1,   "سیگاری بودن",                          "Smoker"),
    "alco":              (lambda v: v == 1,   "مصرف الکل",                            "Alcohol consumption"),
    "active":            (lambda v: v == 0,   "عدم فعالیت بدنی",                      "Physical inactivity"),
    "bmi":               (lambda v: v > 30,   "اضافه وزن / چاقی (BMI>30)",           "Overweight/Obese BMI>30"),
    "hypertension_grade":(lambda v: v >= 2,   "هیپرتانسیون درجه ۲+",                 "Hypertension Grade 2+"),
    "cholesterol":       (lambda v: v >= 2,   "کلسترول بالاتر از نرمال (دسته ۲+)",   "Cholesterol above normal"),
    "gluc":              (lambda v: v >= 2,   "گلوکز بالاتر از نرمال (دسته ۲+)",     "Glucose above normal"),
    "cp":                (lambda v: v == 0,   "درد قفسه سینه آنژینی",               "Anginal chest pain"),
    "ca":                (lambda v: v >= 1,   "کاهش جریان کرونری (CA≥1)",            "Coronary artery narrowing ≥1"),
}


class MLRiskPredictor:
    """
    بارگذاری دو مدل انتخابی و انجام استنتاج ریسک قلبی-عروقی.

    استفاده:
        predictor = MLRiskPredictor()
        result = predictor.predict(patient_config)
        # result['combined_score'], result['severity'], result['risk_factors']
    """

    def __init__(
        self,
        models_dir: Path | str = MODELS_DIR,
        hd_model_file:  str = "hd_logisticregression",
        cv_model_file:  str = "cv_catboost",
        hd_scaler_file: str = "hd_scaler",
    ) -> None:
        self.models_dir = Path(models_dir)
        self._hd_model  = None
        self._cv_model  = None
        self._hd_scaler = None
        self._hd_features: List[str] = self._load_feature_list("hd") or HD_FEATURES_DEFAULT
        self._cv_features: List[str] = self._load_feature_list("cv") or CV_FEATURES_DEFAULT

        self._load_models(hd_model_file, cv_model_file, hd_scaler_file)

    # ── Loading ──────────────────────────────────────────────────────────────

    def _load_feature_list(self, tag: str) -> Optional[List[str]]:
        # in: "hd" | "cv"  → out: ["age","sex",...] or None
        path = self.models_dir / f"{tag}_features.json"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                return json.load(f)
        return None

    def _load_models(self, hd_file: str, cv_file: str, scaler_file: str) -> None:
        # هر سه فایل را با .pkl/.joblib جستجو و در self._hd_model / _cv_model / _hd_scaler ست می‌کند
        for attr, fname, label in [
            ("_hd_model",  hd_file,     "HD_LogisticRegression"),
            ("_cv_model",  cv_file,     "CV_CatBoost"),
            ("_hd_scaler", scaler_file, "HD_Scaler"),
        ]:
            # جستجو برای .pkl یا .joblib
            path = None
            for ext in [".pkl", ".joblib"]:
                candidate = self.models_dir / f"{fname}{ext}"
                if candidate.exists():
                    path = candidate
                    break
            
            if path:
                try:
                    setattr(self, attr, joblib.load(path))
                except Exception as e:
                    warnings.warn(f"خطا در بارگذاری {label}: {e}")
            else:
                warnings.warn(f"{label} یافت نشد: {fname}.pkl یا {fname}.joblib")

    # ── Feature Engineering (دقیقاً مطابق Cell 5 notebook) ───────────────────

    @staticmethod
    def _parse_gender_cv(raw: Dict[str, Any]) -> float:
        # in: {"gender": 2} | {"gender": "male"} | {"sex": 1}  → out: 1.0(زن) | 2.0(مرد)
        g = raw.get("gender", raw.get("sex", 1))
        if isinstance(g, str):
            return 2.0 if g.lower() in ("male", "مرد", "m", "2") else 1.0
        v = float(g) if g is not None else 1.0
        return v if v in (1.0, 2.0) else 1.0

    @staticmethod
    def _parse_gender_hd(raw: Dict[str, Any]) -> float:
        # in: {"sex": 1} | {"sex": "female"} | {"gender": 2}  → out: 0.0(زن) | 1.0(مرد)
        g = raw.get("sex", raw.get("gender", 1))
        if isinstance(g, str):
            return 1.0 if g.lower() in ("male", "مرد", "m", "2") else 0.0
        v = float(g) if g is not None else 1.0
        return 1.0 if v in (1.0, 2.0) else 0.0

    @staticmethod
    def _engineer_hd(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        in : {"age":54, "sex":1, "trestbps":130, "thalach":150, "oldpeak":1.2, ...}
        out: همان + {"bp_category":2.0, "rate_pressure_product":195.0,
            "chronotropic_index":0.91, "st_depression_index":0.8, "age_st_depression":64.8}
        """
        d: Dict[str, Any] = dict(raw)
        d["sex"] = MLRiskPredictor._parse_gender_hd(raw)

        if "trestbps" in d:
            sbp = float(d["trestbps"])
            for hi, lbl in zip([120, 130, 140, 160, float("inf")], [0, 1, 2, 3, 4]):
                if sbp <= hi:
                    d["bp_category"] = float(lbl)
                    break

        if "thalach" in d and "trestbps" in d:
            d["rate_pressure_product"] = float(d["thalach"]) * float(d["trestbps"]) / 100

        age = d.get("age")
        thalach = d.get("thalach")
        if age and thalach and (220 - float(age)) > 0:
            d["chronotropic_index"] = float(thalach) / (220 - float(age))

        oldpeak = d.get("oldpeak")
        if oldpeak is not None and thalach and float(thalach) > 0:
            d["st_depression_index"] = float(oldpeak) / (float(thalach) / 100)

        if age is not None and oldpeak is not None:
            d["age_st_depression"] = float(age) * float(oldpeak)

        return d

    @staticmethod
    def _engineer_cv(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        in : {"age":24, "gender":2, "height":184, "weight":75, "ap_hi":120, "ap_lo":80, ...}
        out: همان + {"bmi":22.1, "bmi_category":1.0, "map":93.3, "pulse_pressure":40.0,
                     "hypertension_grade":0.0, "metabolic_risk_score":0.0,
                     "lifestyle_risk_score":-1.5, "age_bmi_interaction":5.3,
                     "age_hypertension_interaction":0.0}
        """
        d: Dict[str, Any] = dict(raw)
        d["gender"] = MLRiskPredictor._parse_gender_cv(raw)

        # BMI
        h = d.get("height")
        w = d.get("weight")
        if h and w and float(h) > 0:
            h_m = float(h) / 100.0
            bmi = float(w) / (h_m ** 2)
            d["bmi"] = round(bmi, 2)
            for thresh, cat in [(18.5, 0), (25, 1), (30, 2), (35, 3), (40, 4)]:
                if bmi < thresh:
                    d["bmi_category"] = float(cat)
                    break
            else:
                d["bmi_category"] = 5.0

        # Blood pressure derived
        ap_hi = d.get("ap_hi")
        ap_lo = d.get("ap_lo")
        if ap_hi is not None and ap_lo is not None:
            s, dv = float(ap_hi), float(ap_lo)
            d["map"]            = round(dv + (s - dv) / 3, 2)
            d["pulse_pressure"] = round(s - dv, 2)
            # ESC/ESH hypertension grade
            if   s >= 180 or dv >= 110: d["hypertension_grade"] = 4.0
            elif s >= 160 or dv >= 100: d["hypertension_grade"] = 3.0
            elif s >= 140 or dv >= 90:  d["hypertension_grade"] = 2.0
            elif s >= 130 or dv >= 85:  d["hypertension_grade"] = 1.0
            else:                        d["hypertension_grade"] = 0.0

        # Metabolic risk score (weighted)
        score = 0.0
        bmi_val = d.get("bmi", 0)
        if bmi_val:
            score += (bmi_val > 30) * 2.0 + (bmi_val > 35) * 1.5
        ht_grade = d.get("hypertension_grade", 0) #Grade 1: +1.5
        if ht_grade: score += ht_grade * 1.5
        chol = d.get("cholesterol")
        if chol: score += (float(chol) - 1) * 2.0
        gluc = d.get("gluc")
        if gluc: score += (float(gluc) - 1) * 1.5
        smoke = d.get("smoke", 0)
        if smoke: score += float(smoke) * 3.0
        alco = d.get("alco", 0)
        if alco: score += float(alco) * 1.5
        d["metabolic_risk_score"] = round(score, 2)

        # Lifestyle risk score
        ls = 0.0
        if smoke: ls += float(smoke) * 3.0
        if alco:  ls += float(alco) * 2.0
        active = d.get("active", 1)
        if active is not None: ls -= float(active) * 1.5
        d["lifestyle_risk_score"] = round(ls, 2)

        # Age interaction terms
        age = d.get("age")
        if age:
            if "bmi" in d:
                d["age_bmi_interaction"] = round(float(age) * d["bmi"] / 100, 3)
            if "hypertension_grade" in d:
                d["age_hypertension_interaction"] = round(float(age) * d["hypertension_grade"], 2)

        return d

    # ── Vector building & imputation ─────────────────────────────────────────

    @staticmethod
    def _build_vector(
        engineered: Dict[str, Any],
        features:   List[str],
    ) -> Tuple[np.ndarray, float, List[str]]:
        """
        in : engineered dict + لیست feature های مرتب‌شده مدل
        out: (array shape(1,n), confidence 0-1, missing_names[])
             مقادیر غایب → CLINICAL_MEDIANS → 0.0
             confidence = تعداد فیچر واقعی / کل فیچرها
        """
        vec:     List[float] = []
        missing: List[str]   = []

        for feat in features:
            val = engineered.get(feat)
            is_nan = isinstance(val, float) and math.isnan(val)
            if val is not None and not is_nan:
                vec.append(float(val))
            elif feat in CLINICAL_MEDIANS:
                vec.append(float(CLINICAL_MEDIANS[feat]))
                missing.append(feat)
            else:
                vec.append(0.0)
                missing.append(feat)

        n_provided = len(features) - len(missing)
        confidence = round(n_provided / max(len(features), 1), 3)
        return np.array(vec, dtype=np.float64).reshape(1, -1), confidence, missing

    # ── Per-model prediction ─────────────────────────────────────────────────

    def _predict_hd(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        """
        in : patient dict (raw از MongoDB)
        out: {"model":"HD_LogisticRegression", "probability":0.7279, "probability_pct":72.8,
              "confidence":1.0, "missing_features":[], "n_features_used":18, "_engineered":{...}}
             یا {"error":"..."} اگر مدل لود نشده باشد
        """
        if self._hd_model is None:
            return {
                "model": "HD_LogisticRegression", "probability": 0.5,
                "confidence": 0.0, "missing_features": [],
                "error": "مدل بارگذاری نشده — فایل hd_logisticregression.joblib بررسی شود"
            }

        eng = self._engineer_hd(patient)
        vec, conf, missing = self._build_vector(eng, self._hd_features)

        # LogisticRegression به StandardScaler نیاز دارد
        if self._hd_scaler is not None:
            vec = self._hd_scaler.transform(vec)

        prob = float(self._hd_model.predict_proba(vec)[0, 1])
        return {
            "model":            "HD_LogisticRegression",
            "probability":      round(prob, 4),
            "probability_pct":  round(prob * 100, 1),
            "confidence":       conf,
            "missing_features": missing,
            "n_features_used":  len(self._hd_features) - len(missing),
            "_engineered":      eng,   # برای تشخیص عوامل خطر (داخلی)
        }

    def _predict_cv(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        """
        in : patient dict (raw از MongoDB)
        out: {"model":"CV_CatBoost", "probability":0.0924, "probability_pct":9.2,
              "confidence":1.0, "missing_features":[], "n_features_used":20, "_engineered":{...}}
             یا {"error":"..."} اگر مدل لود نشده باشد
        """
        if self._cv_model is None:
            return {
                "model": "CV_CatBoost", "probability": 0.5,
                "confidence": 0.0, "missing_features": [],
                "error": "مدل بارگذاری نشده — فایل cv_catboost.joblib بررسی شود"
            }

        eng = self._engineer_cv(patient)
        vec, conf, missing = self._build_vector(eng, self._cv_features)

        # CatBoost نیازی به scaling ندارد
        prob = float(self._cv_model.predict_proba(vec)[0, 1])
        return {
            "model":            "CV_CatBoost",
            "probability":      round(prob, 4),
            "probability_pct":  round(prob * 100, 1),
            "confidence":       conf,
            "missing_features": missing,
            "n_features_used":  len(self._cv_features) - len(missing),
            "_engineered":      eng,
        }

    # ── Risk factor detection ────────────────────────────────────────────────

    @staticmethod
    def _detect_risk_factors(
        hd_eng: Dict[str, Any],
        cv_eng: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        in : دو dict engineered (HD و CV)
        out: [{"feature":"ca","value":2,"label_fa":"کاهش جریان کرونری","label_en":"..."},...]
             فقط فیچرهایی که rule شان True شده (از RISK_FACTOR_DEFS)
        """
        combined = {**hd_eng, **cv_eng}
        found: List[Dict[str, Any]] = []

        for feat, (rule, label_fa, label_en) in RISK_FACTOR_DEFS.items():
            val = combined.get(feat)
            if val is None:
                continue
            try:
                if rule(val):
                    found.append({
                        "feature":  feat,
                        "value":    round(float(val), 2) if isinstance(val, float) else val,
                        "label_fa": label_fa,
                        "label_en": label_en,
                    })
            except Exception as e:
                warnings.warn(f"خطا در بررسی عامل خطر {feat}: {e}")

        return found

    # ── Public API ───────────────────────────────────────────────────────────

    def predict(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        in : {"age":24, "sex":1, "gender":2, "height":184, "weight":75,
               "ap_hi":120, "ap_lo":80, "cholesterol":1, "gluc":1,
               "smoke":0, "alco":0, "active":1,
               "cp":0, "trestbps":130, "chol":200, "thalach":160,
               "exang":0, "oldpeak":0.5, "slope":1, "ca":2, "thal":2}
             فیلدهای غایب از CLINICAL_MEDIANS جایگزین می‌شوند

        out: {"hd_result":   {probability, probability_pct, confidence, missing_features},
              "cv_result":   {probability, probability_pct, confidence, missing_features},
              "combined_score": 41.0,    # میانگین وزنی × 100
              "combined_prob":  0.4102,
              "severity":       "LOW",   # LOW(<0.45) | MODERATE(0.45-0.70) | HIGH(≥0.70)
              "risk_factors":   [...],
              "bmi":            22.1,
              "confidence":     1.0}
        """
        hd = self._predict_hd(patient_data)
        cv = self._predict_cv(patient_data)

        hd_conf   = hd.get("confidence", 0.0)
        cv_conf   = cv.get("confidence", 0.0)
        total_conf = hd_conf + cv_conf

        if total_conf > 0:
            combined_prob = (
                hd["probability"] * hd_conf +
                cv["probability"] * cv_conf
            ) / total_conf
        else:
            combined_prob = (hd["probability"] + cv["probability"]) / 2

        combined_score  = round(combined_prob * 100, 1)
        avg_confidence  = round((hd_conf + cv_conf) / 2, 3)

        if   combined_prob >= 0.70: severity = "HIGH"
        elif combined_prob >= 0.45: severity = "MODERATE"
        else:                       severity = "LOW"

        # عوامل خطر از هر دو feature set
        risk_factors = self._detect_risk_factors(
            hd.get("_engineered", {}),
            cv.get("_engineered", {}),
        )

        # BMI (از CV engineering)
        bmi_val = cv.get("_engineered", {}).get("bmi")

        # حذف فیلدهای داخلی از خروجی نهایی
        for r in (hd, cv):
            r.pop("_engineered", None)

        return {
            "hd_result":      hd,
            "cv_result":      cv,
            "combined_score": combined_score,
            "combined_prob":  round(combined_prob, 4),
            "severity":       severity,
            "risk_factors":   risk_factors,
            "bmi":            round(bmi_val, 1) if bmi_val else None,
            "confidence":     avg_confidence,
        }