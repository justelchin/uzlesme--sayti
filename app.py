import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Üzləşmə Aktı Portalı", layout="wide")

st.title("📊 Debitor və Kreditor Üzləşmə Portalı")

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

def clean_number(val):
    if pd.isna(val):
        return 0.0
    val_str = str(val).upper().replace("AZN", "").replace(" ", "").strip()
    if not val_str or val_str == "NONE" or val_str == "NAN":
        return 0.0
    val_str = val_str.replace(",", ".")
    try:
        res = re.findall(r"[-+]?\d*\.\d+|\d+", val_str)
        return float(res[0]) if res else 0.0
    except:
        return 0.0

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
                if any(k in row_str for k in ["tarix", "qaimə", "məbləğ", "alıcı", "adı"]):
                    header_row = i
                    break
            else:
                if any(k in row_str for k in ["bank", "çıxarış", "silinmə", "daxil olma", "kontragent", "azn"]):
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
    
    # Sol Paneldə Sütun Təyinatı
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Məbləğ Sütunlarını Dəqiqləşdirin")
    
    q_cols = df_qaime.columns.tolist() if df_qaime is not None else []
    o_cols = df_odenis.columns.tolist() if df_odenis is not None else []
    
    # Avtomatik default indeksləri tapmaq
    q_mbl_idx = next((i for i, c in enumerate(q_cols) if any(x in c.lower() for x in ["yekun", "məbləğ", "cəmi"])), 0) if q_cols else 0
    o_mbl_idx = next((i for i, c in enumerate(o_cols) if any(x in c.lower() for x in ["silinmə", "daxil", "məbləğ", "12240"])), 0) if o_cols else 0
    
    q_mebleg_col = st.sidebar.selectbox("Qaimə Məbləğ Sütunu", q_cols, index=q_mbl_idx) if q_cols else None
    o_mebleg_col = st.sidebar.selectbox("Ödəniş Məbləğ Sütunu", o_cols, index=o_mbl_idx) if o_cols else None

    # Avtomatik digər sütunlar
    q_tarix_col = next((c for c in q_cols if "tarix" in c.lower()), q_cols[0] if q_cols else None)
    q_musteri_col = next((c for c in q_cols if any(x in c.lower() for x in ["adı", "müştəri", "alıcı"])), q_cols[0] if q_cols else None)
    q_sened_col = next((c for c in q_cols if any(x in c.lower() for x in ["nömrə", "№", "sənəd"])), q_cols[0] if q_cols else None)

    o_tarix_col = next((c for c in o_cols if "tarix" in c.lower() or "keçirilib" in c.lower()), o_cols[0] if o_cols else None)
    o_musteri_col = next((c for c in o_cols if any(x in c.lower() for x in ["kontragent", "müştəri", "ödəyən"])), o_cols[0] if o_cols else None)
    o_sened_col = next((c for c in o_cols if any(x in c.lower() for x in ["təyinat", "açıqlama"])), o_cols[0] if o_cols else None)

    musteriler_list = []
    if df_qaime is not None and q_musteri_col:
        raw_m = df_qaime[q_musteri_col].dropna().astype(str).unique().tolist()
        musteriler_list = sorted([m for m in raw_m if m.strip() and not m.startswith("Unnamed") and m.lower() not in ["none", "nan"]])

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
        
        # 1. Qaimələr (Debet)
        if df_qaime is not None and q_musteri_col:
            q_df = df_qaime[df_qaime[q_musteri_col].astype(str) == secilmis_musteri].copy()
            q_df[q_tarix_col] = pd.to_datetime(q_df[q_tarix_col], errors='coerce')
            q_df = q_df.dropna(subset=[q_tarix_col])
            
            for _, row in q_df.iterrows():
                mblg = clean_number(row[q_mebleg_col]) if q_mebleg_col else 0.0
                snd = str(row[q_sened_col]) if q_sened_col and pd.notna(row[q_sened_col]) else ""
                combined_rows.append({
                    "Tarix": row[q_tarix_col],
                    "Növ": "Qaimə",
                    "Sənəd №": snd,
                    "Debet": mblg,
                    "Kredit": 0.0
                })
        
        # 2. Ödənişlər (Kredit)
        if df_odenis is not None:
            o_df = df_odenis.copy()
            o_df[o_tarix_col] = pd.to_datetime(o_df[o_tarix_col], errors='coerce')
            o_df = o_df.dropna(subset=[o_tarix_col])
            
            for _, row in o_df.iterrows():
                val_m = normalize_text(row[o_musteri_col]) if o_musteri_col in row else ""
                val_s = normalize_text(row[o_sened_col]) if o_sened_col in row else ""
                
                if (target_norm in val_m) or (target_norm in val_s) or (val_m in target_norm and len(val_m) > 3):
                    mblg = clean_number(row[o_mebleg_col]) if o_mebleg_col else 0.0
                    snd = str(row[o_sened_col]) if o_sened_col and pd.notna(row[o_sened_col]) else "Ödəniş"
                    combined_rows.append({
                        "Tarix": row[o_tarix_col],
                        "Növ": "Ödəniş",
                        "Sənəd №": snd[:30],
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
                "Qalıq": f"{ilkin_qaliq:,.2f}"
            }]
            
            cari_qaliq = ilkin_qaliq
            for _, row in dovr_df.iterrows():
                debet = row["Debet"]
                kredit = row["Kredit"]
                cari_qaliq += (debet - kredit)
                
                akt_rows.append({
                    "Tarix": row["Tarix"].strftime("%d.%m.%Y"),
                    "Əməliyyat / Sənəd №": f"{row['Növ']} - {row['Sənəd №']}",
                    "Debet (Borc)": f"{debet:,.2f}" if debet > 0 else "-",
                    "Kredit (Alacaq)": f"{kredit:,.2f}" if kredit > 0 else "-",
                    "Qalıq": f"{cari_qaliq:,.2f}"
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
