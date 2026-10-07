import os
import uuid
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# --- SAYFA YAPISI ---
st.set_page_config(page_title="T1D Karb & Gıda Kayıt", layout="wide", page_icon="🍽️")

# --- ÖZEL KOYU YEŞİL & SİYAH TEMASI (CSS) ---
st.markdown("""
<style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #080c0a;
        color: #e2e8f0;
    }
    
    /* Üst Başlık ve Yazılar */
    h1, h2, h3, h4, h5, h6, p, span {
        color: #e2e8f0 !important;
    }
    
    /* Sidebar (Sol Menü) */
    [data-testid="stSidebar"] {
        background-color: #040705;
        border-right: 1px solid #112217;
    }
    
    /* Butonlar (Zümrüt Yeşili Gradyan) */
    .stButton>button {
        background: linear-gradient(135deg, #059669, #047857);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.2);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #10b981, #059669);
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
        border-color: #10b981;
    }
    
    /* Girdi Kutuları (Input / Textarea) */
    input, textarea, select {
        background-color: #0e1712 !important;
        color: #f8fafc !important;
        border: 1px solid #163020 !important;
        border-radius: 8px !important;
    }
    input:focus, textarea:focus {
        border-color: #10b981 !important;
        box-shadow: 0 0 0 1px #10b981 !important;
    }
    
    /* Sekmeler (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #0e1712;
        border-radius: 8px;
        color: #94a3b8;
        padding: 8px 16px;
        border: 1px solid #163020;
    }
    .stTabs [aria-selected="true"] {
        background-color: #065f46 !important;
        color: #ffffff !important;
        border-color: #10b981 !important;
    }
    
    /* Kartlar ve Konteynerler */
    [data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #0e1712;
        border: 1px solid #163020;
        border-radius: 12px;
        padding: 1rem;
    }
    
    /* Expander Tasarımı */
    .streamlit-expanderHeader {
        background-color: #0e1712;
        border: 1px solid #163020;
        border-radius: 8px;
        color: #10b981 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🍽️Karbonhidrat Sayım Kayıt Asistanı🍽️")
st.caption("ESOGU 200kg diyetisyen kadına inat kendim için yaptım.")

# --- BAĞLANTI (Secrets veya Sol Menü) ---
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
BUCKET_NAME = "meal-images"

def insert_meal(food_name, weight_g, carbs_g, protein_g, fat_g, kio, image_file, notes):
    file_bytes = image_file.getvalue()
    ext = os.path.splitext(image_file.name)[1] if hasattr(image_file, "name") else ".jpg"
    file_name = f"{uuid.uuid4().hex}{ext}"

    supabase.storage.from_(BUCKET_NAME).upload(
        file_name, file_bytes, {"content-type": "image/jpeg"}
    )
    image_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_name)

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
    try:
        res = supabase.table("meals").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

def delete_meal(meal_id, image_url):
    try:
        supabase.table("meals").delete().eq("id", meal_id).execute()
        if image_url:
            file_name = image_url.split("/")[-1]
            supabase.storage.from_(BUCKET_NAME).remove([file_name])
    except Exception as e:
        st.error(f"Silme sırasında hata oluştu: {e}")

# --- SEKMELER ---
tab_add, tab_history, tab_dataset = st.tabs([
    "➕ Yeni Öğün Kaydet",
    "📚 Geçmiş & Görseller",
    "📊 Veri Seti Dışa Aktar"
])

with tab_add:
    st.subheader("Öğün Bilgilerini Gir")
    col_img, col_inputs = st.columns([1, 1])

    with col_img:
        photo_mode = st.radio("Fotoğraf Giriş Yöntemi", ["Dosya Yükle", "Kamera ile Çek"], horizontal=True)
        uploaded_image = None
        if photo_mode == "Kamera ile Çek":
            uploaded_image = st.camera_input("Tabağın fotoğrafını çek (kuşbakışı veya 45°)")
        else:
            uploaded_image = st.file_uploader("Tabak görseli seç", type=["jpg", "jpeg", "png", "webp"])

        if uploaded_image:
            st.image(uploaded_image, caption="Önizleme", use_container_width=True)

    with col_inputs:
        food_name = st.text_input("Besin Adı / Tanımı *", placeholder="Örn: Haşlanmış Basmati Pirinç (Beyaz Kase)")

        col_w, col_c = st.columns(2)
        with col_w:
            weight_g = st.number_input("Tartılan Net Ağırlık (Gram) *", min_value=1.0, max_value=2500.0, value=150.0, step=1.0)
        with col_c:
            carbs_g = st.number_input("Net Karbonhidrat (Gram) *", min_value=0.0, max_value=500.0, value=35.0, step=0.5)

        with st.expander("Ekstra Besin Değerleri & İnsülin Ayarı", expanded=False):
            col_p, col_f = st.columns(2)
            with col_p:
                protein_g = st.number_input("Protein (g)", min_value=0.0, value=0.0, step=0.5)
            with col_f:
                fat_g = st.number_input("Yağ (g)", min_value=0.0, value=0.0, step=0.5)

            kio = st.number_input(
                "KİO (Karbonhidrat/İnsülin Oranı - 1 Ünite kaç gram karb?)",
                min_value=1.0, max_value=50.0, value=10.0, step=0.5
            )

        notes = st.text_area("Notlar", placeholder="Kullanılan tabak (küçük mavi kase), yağ miktarı vb.")

        if weight_g > 0:
            c100 = (carbs_g / weight_g) * 100
            s_ins = carbs_g / kio if kio > 0 else 0
            st.info(f"💡 **100g Başına Karb:** `{c100:.1f}g` | **Tahmini İnsülin:** `{s_ins:.1f} Ünite`")

        submit_btn = st.button("💾 Öğünü Veri Setine Kaydet", type="primary", use_container_width=True)

        if submit_btn:
            if not food_name.strip():
                st.error("Lütfen besin adını belirtin.")
            elif uploaded_image is None:
                st.error("Lütfen tabağın bir fotoğrafını ekleyin.")
            else:
                with st.spinner("Kaydediliyor..."):
                    insert_meal(food_name, weight_g, carbs_g, protein_g, fat_g, kio, uploaded_image, notes)
                    st.success(f"'{food_name}' başarıyla kaydedildi!")
                    st.rerun()

with tab_history:
    df_meals = get_all_meals()
    st.subheader(f"Kayıtlı Öğünler ({len(df_meals)} adet)")

    if df_meals.empty:
        st.info("Henüz kaydedilmiş bir öğün bulunmuyor.")
    else:
        search_query = st.text_input("Besin adına göre filtrele", "")
        if search_query:
            df_meals = df_meals[df_meals["food_name"].str.contains(search_query, case=False, na=False)]

        for _, row in df_meals.iterrows():
            with st.container(border=True):
                col_card_img, col_card_info, col_card_del = st.columns([1.2, 2.5, 0.5])

                with col_card_img:
                    if row.get("image_url"):
                        st.image(row["image_url"], use_container_width=True)
                    else:
                        st.warning("Görsel bulunamadı")

                with col_card_info:
                    st.markdown(f"### {row['food_name']}")
                    st.markdown(f"**Ağırlık:** `{row['weight_g']} g` | **Karb:** `{row['carbs_g']} g` *(100g: {row['carbs_per_100g']}g)*")
                    st.markdown(f"**Protein:** `{row['protein_g']} g` | **Yağ:** `{row['fat_g']} g`")
                    st.markdown(f"**Önerilen İnsülin (KİO 1:{row.get('kio', 10)}):** `{row.get('suggested_insulin', 0)} Ünite`")
                    if row.get("notes"):
                        st.caption(f"📝 {row['notes']}")
                    st.caption(f"Tarih: {row.get('created_at', '')}")

                with col_card_del:
                    if st.button("🗑️ Sil", key=f"del_{row['id']}"):
                        delete_meal(row["id"], row.get("image_url"))
                        st.rerun()

with tab_dataset:
    st.subheader("Model Eğitimi İçin Veri Çıktısı")
    st.write("Bu tablo, ileride DINOv2 / CLIP embedding vektörlerini veya YOLO modellerini beslemek için kullanılacak meta veridir.")

    df_export = get_all_meals()
    if not df_export.empty:
        st.dataframe(df_export, use_container_width=True)
        csv = df_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 CSV Formatında İndir",
            data=csv,
            file_name=f"t1d_meals_dataset_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Dışa aktarılacak veri bulunamadı.")
