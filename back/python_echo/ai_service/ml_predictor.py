from __future__ import annotations

import json
import math
import os
import warnings
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np

MODELS_DIR = Path(os.getenv("CARDIOAI_MODELS_DIR", Path(__file__).resolve().parent / "models"))

HD_FEATURES_DEFAULT: list[str] = [
    "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
    "thalach", "exang", "oldpeak", "slope", "ca", "thal",
    "bp_category", "rate_pressure_product", "chronotropic_index",
    "st_depression_index", "age_st_depression",
]

CV_FEATURES_DEFAULT: list[str] = [
    "age", "gender", "height", "weight",
    "ap_hi", "ap_lo", "cholesterol", "gluc", "smoke", "alco", "active",
    "bmi", "bmi_category", "map", "pulse_pressure", "hypertension_grade",
    "metabolic_risk_score", "lifestyle_risk_score",
    "age_bmi_interaction", "age_hypertension_interaction",
]

CLINICAL_MEDIANS: dict[str, float] = {
    "age": 54.0, "sex": 1.0, "cp": 0.0, "trestbps": 130.0,
    "chol": 240.0, "fbs": 0.0, "restecg": 0.0, "thalach": 149.0,
    "exang": 0.0, "oldpeak": 0.8, "slope": 1.0, "ca": 0.0, "thal": 2.0,
    "bp_category": 1.0, "rate_pressure_product": 193.7,
    "chronotropic_index": 0.916, "st_depression_index": 0.54,
    "age_st_depression": 43.2,
    "gender": 1.0, "height": 165.0, "weight": 72.0,
    "ap_hi": 120.0, "ap_lo": 80.0, "cholesterol": 1.0, "gluc": 1.0,
    "smoke": 0.0, "alco": 0.0, "active": 1.0,
    "bmi": 26.5, "bmi_category": 1.0, "map": 93.3,
    "pulse_pressure": 40.0, "hypertension_grade": 0.0,
    "metabolic_risk_score": 0.0, "lifestyle_risk_score": -1.5,
    "age_bmi_interaction": 14.3, "age_hypertension_interaction": 0.0,
}

# (rule, label_fa, label_en)
RISK_FACTOR_DEFS: dict[str, tuple] = {
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
    """بارگذاری مدل‌های HD/CV و پیش‌بینی ریسک قلبی-عروقی"""

    def __init__(
        self,
        models_dir: Path | str = MODELS_DIR,
        hd_model_file:  str = "hd_logisticregression",
        cv_model_file:  str = "cv_catboost",
        hd_scaler_file: str = "hd_scaler",
    ) -> None:
        # فقط یک‌بار در main.get_ml_predictor ساخته می‌شه (سینگلتون) — همینجا مدل‌ها از دیسک لود می‌شن
        self.models_dir   = Path(models_dir)
        self._hd_model    = None
        self._cv_model    = None
        self._hd_scaler   = None
        self._hd_features = self._load_feature_list("hd") or HD_FEATURES_DEFAULT
        self._cv_features = self._load_feature_list("cv") or CV_FEATURES_DEFAULT
        self._load_models(hd_model_file, cv_model_file, hd_scaler_file)

    def _load_feature_list(self, tag: str) -> list[str] | None:
        # in: "hd" | "cv"  → out: feature list or None
        path = self.models_dir / f"{tag}_features.json"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                return json.load(f)
        return None

    def _load_models(self, hd_file: str, cv_file: str, scaler_file: str) -> None:
        for attr, fname, label in [
            ("_hd_model",  hd_file,     "HD_LogisticRegression"),
            ("_cv_model",  cv_file,     "CV_CatBoost"),
            ("_hd_scaler", scaler_file, "HD_Scaler"),
        ]:
            path = next(
                (self.models_dir / f"{fname}{ext}" for ext in (".pkl", ".joblib")
                 if (self.models_dir / f"{fname}{ext}").exists()),
                None,
            )
            if path:
                try:
                    setattr(self, attr, joblib.load(path))
                except Exception as exc:
                    warnings.warn(f"خطا در بارگذاری {label}: {exc}")
            else:
                warnings.warn(f"{label} یافت نشد: {fname}.pkl یا {fname}.joblib")

    # ── Feature Engineering ───────────────────────────────────────────────────

    @staticmethod
    def _parse_gender_cv(raw: dict[str, Any]) -> float:
        # in: {"gender": 2} | {"gender": "male"} | {"sex": 1}  → out: 1.0(زن) | 2.0(مرد)
        g = raw.get("gender", raw.get("sex", 1))
        if isinstance(g, str):
            return 2.0 if g.lower() in ("male", "مرد", "m", "2") else 1.0
        v = float(g) if g is not None else 1.0
        return v if v in (1.0, 2.0) else 1.0

    @staticmethod
    def _parse_gender_hd(raw: dict[str, Any]) -> float:
        # in: {"sex": 1} | {"sex": "female"} | {"gender": 2}  → out: 0.0(زن) | 1.0(مرد)
        g = raw.get("sex", raw.get("gender", 1))
        if isinstance(g, str):
            return 1.0 if g.lower() in ("male", "مرد", "m", "2") else 0.0
        v = float(g) if g is not None else 1.0
        return 1.0 if v in (1.0, 2.0) else 0.0

    @staticmethod
    def _engineer_hd(raw: dict[str, Any]) -> dict[str, Any]:
        # in:  {"age":54, "sex":1, "trestbps":130, "thalach":150, "oldpeak":1.2, ...}
        # out: همان + bp_category, rate_pressure_product, chronotropic_index, st_depression_index, age_st_depression
        d = dict(raw)
        d["sex"] = MLRiskPredictor._parse_gender_hd(raw)
        if "trestbps" in d:
            sbp = float(d["trestbps"])
            for hi, lbl in zip([120, 130, 140, 160, float("inf")], [0, 1, 2, 3, 4]):
                if sbp <= hi:
                    d["bp_category"] = float(lbl)
                    break
        if "thalach" in d and "trestbps" in d:
            d["rate_pressure_product"] = float(d["thalach"]) * float(d["trestbps"]) / 100
        age, thalach = d.get("age"), d.get("thalach")
        if age and thalach and (220 - float(age)) > 0:
            d["chronotropic_index"] = float(thalach) / (220 - float(age))
        oldpeak = d.get("oldpeak")
        if oldpeak is not None and thalach and float(thalach) > 0:
            d["st_depression_index"] = float(oldpeak) / (float(thalach) / 100)
        if age is not None and oldpeak is not None:
            d["age_st_depression"] = float(age) * float(oldpeak)
        return d

    @staticmethod
    def _engineer_cv(raw: dict[str, Any]) -> dict[str, Any]:
        # in:  {"age":24, "gender":2, "height":184, "weight":75, "ap_hi":120, "ap_lo":80, ...}
        # out: همان + bmi, bmi_category, map, pulse_pressure, hypertension_grade, metabolic/lifestyle risk scores, age interactions
        d = dict(raw)
        d["gender"] = MLRiskPredictor._parse_gender_cv(raw)
        h, w = d.get("height"), d.get("weight")
        if h and w and float(h) > 0:
            bmi = float(w) / (float(h) / 100) ** 2
            d["bmi"] = round(bmi, 2)
            for thresh, cat in [(18.5, 0), (25, 1), (30, 2), (35, 3), (40, 4)]:
                if bmi < thresh:
                    d["bmi_category"] = float(cat)
                    break
            else:
                d["bmi_category"] = 5.0
        ap_hi, ap_lo = d.get("ap_hi"), d.get("ap_lo")
        if ap_hi is not None and ap_lo is not None:
            s, dv = float(ap_hi), float(ap_lo)
            d["map"]            = round(dv + (s - dv) / 3, 2)
            d["pulse_pressure"] = round(s - dv, 2)
            if   s >= 180 or dv >= 110: d["hypertension_grade"] = 4.0
            elif s >= 160 or dv >= 100: d["hypertension_grade"] = 3.0
            elif s >= 140 or dv >= 90:  d["hypertension_grade"] = 2.0
            elif s >= 130 or dv >= 85:  d["hypertension_grade"] = 1.0
            else:                        d["hypertension_grade"] = 0.0
        bmi_val  = d.get("bmi", 0)
        ht_grade = d.get("hypertension_grade", 0)
        chol     = d.get("cholesterol")
        gluc     = d.get("gluc")
        smoke    = d.get("smoke", 0)
        alco     = d.get("alco", 0)
        active   = d.get("active", 1)
        d["metabolic_risk_score"] = round(
            (bmi_val > 30) * 2.0 + (bmi_val > 35) * 1.5 +
            (ht_grade * 1.5 if ht_grade else 0) +
            ((float(chol) - 1) * 2.0 if chol else 0) +
            ((float(gluc) - 1) * 1.5 if gluc else 0) +
            (float(smoke) * 3.0 if smoke else 0) +
            (float(alco) * 1.5 if alco else 0),
            2,
        )
        d["lifestyle_risk_score"] = round(
            (float(smoke) * 3.0 if smoke else 0) +
            (float(alco) * 2.0 if alco else 0) -
            (float(active) * 1.5 if active is not None else 0),
            2,
        )
        age = d.get("age")
        if age:
            if "bmi" in d:
                d["age_bmi_interaction"] = round(float(age) * d["bmi"] / 100, 3)
            if "hypertension_grade" in d:
                d["age_hypertension_interaction"] = round(float(age) * d["hypertension_grade"], 2)
        return d

    # ── Vector building ───────────────────────────────────────────────────────

    @staticmethod
    def _build_vector(
        engineered: dict[str, Any],
        features:   list[str],
    ) -> tuple[np.ndarray, float, list[str]]:
        # in:  engineered dict, ordered feature list
        # out: (array(1,n), confidence 0-1, missing_names)  — missing → CLINICAL_MEDIANS fallback
        vec:     list[float] = []
        missing: list[str]   = []
        for feat in features:
            val    = engineered.get(feat)
            is_nan = isinstance(val, float) and math.isnan(val)
            if val is not None and not is_nan:
                vec.append(float(val))
            elif feat in CLINICAL_MEDIANS:
                vec.append(float(CLINICAL_MEDIANS[feat]))
                missing.append(feat)
            else:
                vec.append(0.0)
                missing.append(feat)
        confidence = round((len(features) - len(missing)) / max(len(features), 1), 3)
        return np.array(vec, dtype=np.float64).reshape(1, -1), confidence, missing

    # ── Per-model prediction ──────────────────────────────────────────────────

    def _predict_model(
        self,
        patient:      dict[str, Any],
        model:        Any,
        engineer_fn:  Callable,
        features:     list[str],
        model_name:   str,
        scaler:       Any = None,
    ) -> dict[str, Any]:
        # in:  patient dict + model components
        # out: {model, probability, probability_pct, confidence, missing_features, n_features_used, _engineered}
        #      or {error} if model not loaded
        if model is None:
            return {"model": model_name, "probability": 0.5, "confidence": 0.0,
                    "missing_features": [],
                    "error": f"مدل بارگذاری نشده — فایل {model_name.lower().replace(' ', '_')}.joblib بررسی شود"}
        eng = engineer_fn(patient)
        vec, conf, missing = self._build_vector(eng, features)
        if scaler is not None:
            vec = scaler.transform(vec)
        prob = float(model.predict_proba(vec)[0, 1])
        return {
            "model":            model_name,
            "probability":      round(prob, 4),
            "probability_pct":  round(prob * 100, 1),
            "confidence":       conf,
            "missing_features": missing,
            "n_features_used":  len(features) - len(missing),
            "_engineered":      eng,
        }

    def _predict_hd(self, patient: dict[str, Any]) -> dict[str, Any]:
        return self._predict_model(patient, self._hd_model, self._engineer_hd,
                                   self._hd_features, "HD_LogisticRegression", self._hd_scaler)

    def _predict_cv(self, patient: dict[str, Any]) -> dict[str, Any]:
        return self._predict_model(patient, self._cv_model, self._engineer_cv,
                                   self._cv_features, "CV_CatBoost")

    # ── Risk factor detection ─────────────────────────────────────────────────

    @staticmethod
    def _detect_risk_factors(hd_eng: dict[str, Any], cv_eng: dict[str, Any]) -> list[dict[str, Any]]:
        # in:  two engineered dicts (HD + CV)
        # out: [{"feature", "value", "label_fa", "label_en"}, ...]  — only triggered rules
        combined = {**hd_eng, **cv_eng}
        found: list[dict[str, Any]] = []
        for feat, (rule, label_fa, label_en) in RISK_FACTOR_DEFS.items():
            val = combined.get(feat)
            if val is None:
                continue
            try:
                if rule(val):
                    found.append({"feature": feat,
                                  "value":    round(float(val), 2) if isinstance(val, float) else val,
                                  "label_fa": label_fa,
                                  "label_en": label_en})
            except Exception as exc:
                warnings.warn(f"خطا در بررسی عامل خطر {feat}: {exc}")
        return found

    # ── Public API ────────────────────────────────────────────────────────────

    def predict(self, patient_data: dict[str, Any]) -> dict[str, Any]:
        """
        ورودی:  دیکشنری خام بیمار (age, sex/gender, height, weight, ap_hi/lo, ...)
        خروجی:  {hd_result, cv_result, combined_score, combined_prob, severity, risk_factors, bmi, confidence}
        تریس:   main.run_ml_analysis این تابع رو صدا می‌زنه؛ خودش دو مدل مستقل (HD و CV) رو اجرا و ترکیب می‌کنه
        """
        # --- مرحله ۱: پیش‌بینی مستقل با هر دو مدل ---
        hd = self._predict_hd(patient_data)
        cv = self._predict_cv(patient_data)

        # --- مرحله ۲: ترکیب دو احتمال با میانگین وزنی بر اساس confidence هر مدل ---
        hd_conf, cv_conf = hd.get("confidence", 0.0), cv.get("confidence", 0.0)
        total_conf = hd_conf + cv_conf
        combined_prob = (
            (hd["probability"] * hd_conf + cv["probability"] * cv_conf) / total_conf
            if total_conf > 0 else
            (hd["probability"] + cv["probability"]) / 2
        )

        # --- مرحله ۳: تعیین سطح شدت بر اساس آستانه‌های ثابت ---
        if   combined_prob >= 0.70: severity = "HIGH"
        elif combined_prob >= 0.45: severity = "MODERATE"
        else:                       severity = "LOW"

        # --- مرحله ۴: می‌ره داخل _detect_risk_factors و روی فیچرهای مهندسی‌شده‌ی هر دو مدل قانون‌ها رو چک می‌کنه ---
        risk_factors = self._detect_risk_factors(hd.get("_engineered", {}), cv.get("_engineered", {}))
        bmi_val      = cv.get("_engineered", {}).get("bmi")

        # فیچرهای مهندسی‌شده فقط داخلی بودن (برای risk_factors) — قبل از برگردوندن به main.py پاک می‌شن
        for r in (hd, cv):
            r.pop("_engineered", None)

        return {
            "hd_result":      hd,
            "cv_result":      cv,
            "combined_score": round(combined_prob * 100, 1),
            "combined_prob":  round(combined_prob, 4),
            "severity":       severity,
            "risk_factors":   risk_factors,
            "bmi":            round(bmi_val, 1) if bmi_val else None,
            "confidence":     round((hd_conf + cv_conf) / 2, 3),
        }
