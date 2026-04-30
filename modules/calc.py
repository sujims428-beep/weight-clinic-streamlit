from __future__ import annotations
from typing import Any, Optional

def fnum(x: Any) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except Exception:
        return None

def fmt(x: Any, n: int = 1, empty: str = "暂无") -> str:
    v = fnum(x)
    return empty if v is None else f"{v:.{n}f}"

def bmi(weight, height):
    w, h = fnum(weight), fnum(height)
    if not w or not h:
        return None
    return round(w / ((h/100)**2), 2)

def whr(waist, hip):
    w, h = fnum(waist), fnum(hip)
    return None if not w or not h else round(w/h, 2)

def loss(initial, current):
    i, c = fnum(initial), fnum(current)
    return None if not i or c is None else round((i-c)/i*100, 2)

def ideal_weight(height):
    h = fnum(height)
    if not h:
        return None, None, None
    m = h/100
    return round(18.5*m*m,1), round(23.9*m*m,1), round(21.5*m*m,1)

def body_fat_percent(bmi_value, age, sex):
    b, a = fnum(bmi_value), fnum(age)
    if b is None or a is None:
        return None
    sex_v = 1 if sex == "男" else 0
    return round(1.2*b + 0.23*a - 10.8*sex_v - 5.4, 2)

def smm_lee(weight, height, age, sex):
    w, h, a = fnum(weight), fnum(height), fnum(age)
    if w is None or h is None or a is None:
        return None
    sex_v = 1 if sex == "男" else 0
    return round(0.244*w + 7.80*(h/100) + 6.6*sex_v - 0.098*a - 1.2 - 3.3, 2)

def bmr(weight, height, age, sex):
    w, h, a = fnum(weight), fnum(height), fnum(age)
    if w is None or h is None or a is None:
        return None
    return round(10*w + 6.25*h - 5*a + (5 if sex=="男" else -161), 0)

def estimate(patient, visit):
    b = bmi(visit.get("weight_kg"), patient.get("height_cm"))
    bf = body_fat_percent(b, patient.get("age"), patient.get("sex"))
    weight = fnum(visit.get("weight_kg"))
    fat = round(weight*bf/100, 2) if weight is not None and bf is not None else None
    lean = round(weight-fat, 2) if weight is not None and fat is not None else None
    return dict(
        patient_id=patient.get("patient_id"), visit_id=visit.get("visit_id"),
        estimate_date=visit.get("visit_date"), sex=patient.get("sex"),
        age=patient.get("age"), height_cm=patient.get("height_cm"), weight_kg=visit.get("weight_kg"),
        bmi=b, body_fat_percent_est=bf, fat_mass_kg_est=fat, lean_body_mass_kg_est=lean,
        skeletal_muscle_mass_kg_est=smm_lee(visit.get("weight_kg"), patient.get("height_cm"), patient.get("age"), patient.get("sex")),
        basal_metabolism_kcal_est=bmr(visit.get("weight_kg"), patient.get("height_cm"), patient.get("age"), patient.get("sex")),
        race_correction="亚洲", data_source="visit_auto", is_for_trend=True, notes="公式估算值，仅用于同一方法下趋势参考。"
    )

def abnormal(value, text, low, high):
    t = (text or "")
    if "阳性" in t: return "阳性"
    if "阴性" in t: return "阴性"
    v, lo, hi = fnum(value), fnum(low), fnum(high)
    if v is None or (lo is None and hi is None): return "未判断"
    if lo is not None and v < lo: return "降低"
    if hi is not None and v > hi: return "升高"
    return "正常"

LAB_TEMPLATES = [
 ("血糖","空腹血糖","mmol/L",3.9,6.1),("血糖","餐后2小时血糖","mmol/L",3.9,7.8),
 ("血糖","糖化血红蛋白","%",4.0,6.0),("血脂","总胆固醇","mmol/L",0,5.2),
 ("血脂","甘油三酯","mmol/L",0.56,1.70),("血脂","高密度脂蛋白胆固醇","mmol/L",1.0,2.0),
 ("血脂","低密度脂蛋白胆固醇","mmol/L",0,3.37),("肝功能","谷丙转氨酶","U/L",9,50),
 ("肝功能","谷草转氨酶","U/L",15,40),("肾功能","肌酐","μmol/L",45,106),
 ("肾功能","尿素","mmol/L",2.8,7.2),("尿酸","尿酸","μmol/L",155,357),
 ("炎症与营养","超敏C反应蛋白","mg/L",0,3),("炎症与营养","维生素D","ng/mL",30,100),
]
