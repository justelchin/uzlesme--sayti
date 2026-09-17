import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Üzləşmə Aktı Portalı", layout="wide")

st.title("📊 Debitor və Kreditor Üzləşmə Portalı")
st.write("Qaimə və Ödəniş fayllarını yükləyin — sistem sütunları avtomatik tanıyaraq üzləşmə aktını hazırlayacaq.")

st.sidebar.header("📁 Faylları Yükləyin")
qaime_file = st.sidebar.file_uploader("1. Qaimələr Faylı", type=["xlsx", "xls", "csv"])
odenis_file = st.sidebar.file_uploader("2. Ödənişlər Faylı", type=["xlsx", "xls", "csv"])

def normalize_text(text):
    if pd.isna(text):
        return ""
    text = str(text).upper()
    for word in ['"', '”', '“', 'MƏHDUD MƏSULİYYƏTLİ CƏMİYYƏTİ', 'MMC', 'LLC', 'OOO']:
        text = text.replace(word, '')
    return re.sub(r'\s+', ' ', text).strip()

def find_column(df, possible_names):
    """Cədvəldə verilmiş açar sözlərə uyğun gələn ilk sütunu avtomatik tapır"""
    for col in df.columns:
        col_clean = str(col).strip().lower()
        if any(name.lower() in col_clean for name in possible_names):
            return col
    return None

def load_clean_data(uploaded_file, is_qaime=False):
    if uploaded_file is None:
        return None
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None)
            
        header_row = 0
        for i, row in df_raw.iterrows():
            row_str = " ".join([str(val).strip().lower() for val in row.values if pd.notna(val)])
            if is_qaime:
                if ("tarix" in row_str or "çıxarış" in row_str) and ("məbləğ" in row_str or "status" in row_str or "adı" in row_str):
                    header_row = i
                    break
            else:
                if any(k in row_str for k in ["bank tərəfindən", "çıxarış", "silinmə", "daxil olma", "kontragent"]):
                    header_row = i
                    break

        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, skiprows=header_row)
        else:
            df = pd.read_excel(uploaded_file, skiprows=header_row)
            
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Fayl oxunarkən xəta: {e}")
        return None

df_qaime = load_clean_data(qaime_file, is_qaime=True)
df_odenis = load_clean_data(odenis_file, is_qaime=False)

if df_qaime is not None or df_odenis is not None:
    st.markdown("---")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if df_qaime is not None:
            st.subheader("📋 Qaimələr Faylı")
            st.dataframe(df_qaime.head(3))
    with col_p2:
        if df_odenis is not None:
            st.subheader("📋 Ödənişlər Faylı")
            st.dataframe(df_odenis.head(3))

    # Avtomatik sütun təyini
    q_tarix_col = find_column(df_qaime, ["Qaimə tarixi", "Tarix", "Verilmə tarixi"]) if df_qaime is not None else None
    q_musteri_col = find_column(df_qaime, ["Adı", "Müştəri", "Alıcı", "Satıcı"]) if df_qaime is not None else None
    q_mebleg_col = find_column(df_qaime, ["Yekun məbləğ", "Məbləğ", "Cəmi"]) if df_qaime is not None else None
    q_sened_col = find_column(df_qaime, ["Qaimə nömrəsi", "№", "Sənəd"]) if df_qaime is not None else None

    o_tarix_col = find_column(df_odenis, ["Bank tərəfindən keçirilib", "Tarix", "Çıxarış"]) if df_odenis is not None else None
    o_musteri_col = find_column(df_odenis, ["Kontragent", "Ödəyən", "Müştəri"]) if df_odenis is not None else None
    o_mebleg_col = find_column(df_odenis, ["Silinmə", "Daxil olma", "Məbləğ"]) if df_odenis is not None else None
    o_sened_col = find_column(df_odenis, ["Ödənişin təyinatı", "Təyinat", "Açıqlama"]) if df_odenis is not None else None

    # Müştəri siyahısı
    musteriler_list = []
    if df_qaime is not None and q_musteri_col:
        raw_m = df_qaime[q_musteri_col].dropna().astype(str).unique().tolist()
        musteriler_list = sorted([m for m in raw_m if m.strip() and not m.startswith("Unnamed") and m.lower() not in ["none", "nan"]])

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        secilmis_musteri = st.selectbox("Müştərini Seçin", musteriler_list if musteriler_list else ["Məlumat Tapılmadı"])
    with col2:
        bas_tarix = st.date_input("Başlanğıc Tarixi", value=pd.to_datetime("2023-01-01"))
    with col3:
        bit_tarix = st.date_input("Bitiş Tarixi", value=pd.to_datetime("2026-12-31"))
        
    if st.button("🚀 Avtomatik Üzləşmə Aktı Yarat"):
        combined_rows = []
        target_norm = normalize_text(secilmis_musteri)
        
        # 1. Qaimələri oxumaq (Debet)
        if df_qaime is not None and q_musteri_col:
            q_df = df_qaime[df_qaime[q_musteri_col].astype(str) == secilmis_musteri].copy()
            q_df[q_tarix_col] = pd.to_datetime(q_df[q_tarix_col], errors='coerce')
            q_df = q_df.dropna(subset=[q_tarix_col])
            
            for _, row in q_df.iterrows():
                mblg = pd.to_numeric(row[q_mebleg_col], errors='coerce') or 0.0
                snd = str(row[q_sened_col]) if q_sened_col and pd.notna(row[q_sened_col]) else ""
                combined_rows.append({
                    "Tarix": row[q_tarix_col],
                    "Növ": "Qaimə",
                    "Sənəd №": snd,
                    "Debet": mblg,
                    "Kredit": 0.0
                })
        
        # 2. Ödənişləri oxumaq (Kredit)
        if df_odenis is not None:
            o_df = df_odenis.copy()
            o_df[o_tarix_col] = pd.to_datetime(o_df[o_tarix_col], errors='coerce')
            o_df = o_df.dropna(subset=[o_tarix_col])
            
            for _, row in o_df.iterrows():
                val_m = normalize_text(row[o_musteri_col]) if o_musteri_col in row else ""
                val_s = normalize_text(row[o_sened_col]) if o_sened_col in row else ""
                
                # Ağıllı Eyniləşdirmə
                if (target_norm in val_m) or (target_norm in val_s) or (val_m in target_norm and len(val_m) > 3):
                    mblg = pd.to_numeric(row[o_mebleg_col], errors='coerce') or 0.0
                    snd = str(row[o_sened_col]) if o_sened_col and pd.notna(row[o_sened_col]) else ""
                    combined_rows.append({
                        "Tarix": row[o_tarix_col],
                        "Növ": "Ödəniş",
                        "Sənəd №": snd[:30],  # Açıqlamanın ilk hissəsi
                        "Debet": 0.0,
                        "Kredit": mblg
                    })
                
        if not combined_rows:
            st.warning("Seçilmiş müştəri üzrə heç bir əməliyyat tapılmadı.")
        else:
            full_df = pd.DataFrame(combined_rows).sort_values(by="Tarix")
            
            bas_tarix_dt = pd.to_datetime(bas_tarix)
            bit_tarix_dt = pd.to_datetime(bit_tarix)
            
            ilkin_df = full_df[full_df["Tarix"] < bas_tarix_dt]
            ilkin_qaliq = ilkin_df["Debet"].sum() - ilkin_df["Kredit"].sum()
            
            dovr_df = full_df[(full_df["Tarix"] >= bas_tarix_dt) & (full_df["Tarix"] <= bit_tarix_dt)]
            
            akt_rows = [{
                "Tarix": "-",
                "Əməliyyat / Sənəd №": "Dövrə qədər olan ilkin qalıq",
                "Debet (Borc)": "-",
                "Kredit (Alacaq)": "-",
                "Qalıq": ilkin_qaliq
            }]
            
            cari_qaliq = ilkin_qaliq
            for _, row in dovr_df.iterrows():
                debet = row["Debet"]
                kredit = row["Kredit"]
                cari_qaliq += (debet - kredit)
                
                akt_rows.append({
                    "Tarix": row["Tarix"].strftime("%d.%m.%Y"),
                    "Əməliyyat / Sənəd №": f"{row['Növ']} - {row['Sənəd №']}",
                    "Debet (Borc)": debet if debet > 0 else "-",
                    "Kredit (Alacaq)": kredit if kredit > 0 else "-",
                    "Qalıq": cari_qaliq
                })
                
            res_df = pd.DataFrame(akt_rows)
            
            st.markdown(f"### 📑 {secilmis_musteri} üzrə Birləşdirilmiş Üzləşmə Aktı")
            st.table(res_df)
            
            csv_data = res_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Üzləşmə Aktını Yüklə (CSV/Excel)",
                data=csv_data,
                file_name=f"Uzlesme_Akti_{secilmis_musteri}.csv",
                mime="text/csv"
            )

else:
    st.info("Zəhmət olmasa faylları yükləyin.")
