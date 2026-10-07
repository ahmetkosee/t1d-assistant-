import streamlit as st
from supabase import create_client, Client
import os
import uuid
import pandas as pd

# Streamlit Secrets'ta hata olursa sol menüden (sidebar) manuel alma imkanı
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.sidebar.warning("⚠️ Secrets okunamadı. Bilgileri buradan girebilirsin:")
    SUPABASE_URL = st.sidebar.text_input("Supabase URL", value="https://hsobtrfmakfhbcnlugkl.supabase.co")
    SUPABASE_KEY = st.sidebar.text_input("Supabase Key (anon public)", type="password")

if not SUPABASE_URL or not SUPABASE_KEY or not SUPABASE_URL.startswith("https://"):
    st.error("🚨 Lütfen sol menüden geçerli bir Supabase URL ve Key girin.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)






















import os
import uuid
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# Streamlit Secrets üzerinden API anahtarlarını al
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_meal(food_name, weight_g, carbs_g, protein_g, fat_g, kio, image_file, notes):
    # 1. Fotoğrafı Supabase Storage'a yükle
    file_bytes = image_file.getvalue()
    file_name = f"{uuid.uuid4().hex}.jpg"
    bucket = "meal-images"

    supabase.storage.from_(bucket).upload(
        file_name, file_bytes, {"content-type": "image/jpeg"}
    )
    image_url = supabase.storage.from_(bucket).get_public_url(file_name)

    # 2. Besin değerlerini hesapla ve tabloya ekle
    carbs_per_100g = (carbs_g / weight_g) * 100 if weight_g > 0 else 0
    suggested_insulin = carbs_g / kio if kio > 0 else 0

    payload = {
        "food_name": food_name.strip(),
        "weight_g": float(weight_g),
        "carbs_g": float(carbs_g),
        "protein_g": float(protein_g),
        "fat_g": float(fat_g),
        "carbs_per_100g": round(carbs_per_100g, 2),
        "kio": float(kio),
        "suggested_insulin": round(suggested_insulin, 2),
        "image_url": image_url,
        "notes": notes.strip()
    }
    supabase.table("meals").insert(payload).execute()

def get_all_meals():
    res = supabase.table("meals").select("*").order("created_at", desc=True).execute()
    return pd.DataFrame(res.data)