import streamlit as st
import pandas as pd

st.set_page_config(page_title="Üzləşmə Aktı Portalı", layout="wide")

st.title("📊 Debitor və Kreditor Üzləşmə Portalı")
st.write("Qaimə və Ödəniş fayllarını ayrı-ayrı yükləyin, sistem avtomatik üzləşmə aktı hazırlasın.")

st.sidebar.header("📁 Faylları Yükləyin")
qaime_file = st.sidebar.file_uploader("1. Qaimələr (Satış/Alış) Faylı", type=["xlsx", "xls", "csv"])
odenis_file = st.sidebar.file_uploader("2. Ödənişlər (Bank/Kassa) Faylı", type=["xlsx", "xls", "csv"])

def load_data(uploaded_file):
    if uploaded_file is None:
        return None
    
    if uploaded_file.name.endswith('.csv'):
        df_raw = pd.read_csv(uploaded_file, header=None)
    else:
        df_raw = pd.read_excel(uploaded_file, header=None)
        
    header_row = 0
    for i, row in df_raw.iterrows():
        row_str = " ".join([str(val).lower() for val in row.values if pd.notna(val)])
        if any(k in row_str for k in ["tarix", "№", "status", "qaimə", "məbləğ", "müştəri", "alınma", "ödəniş"]):
            header_row = i
            break
            
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file, skiprows=header_row)
    else:
        df = pd.read_excel(uploaded_file, skiprows=header_row)
    return df

if qaime_file or odenis_file:
    try:
        df_qaime = load_data(qaime_file)
        df_odenis = load_data(odenis_file)
        
        all_cols = []
        if df_qaime is not None:
            all_cols.extend([str(c) for c in df_qaime.columns.tolist()])
        if df_odenis is not None:
            all_cols.extend([str(c) for c in df_odenis.columns.tolist()])
        
        cols = list(set(all_cols))
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚙️ Sütun Uyğunlaşdırması")
        
        tarix_col = st.sidebar.selectbox("Tarix Sütunu Adı", cols)
        musteri_col = st.sidebar.selectbox("Müştəri Adı Sütunu Adı", cols)
        mebleg_col = st.sidebar.selectbox("Məbləğ Sütunu Adı", cols)
        sened_col = st.sidebar.selectbox("Sənəd № Sütunu Adı", cols)
        
        musteriler = []
        if df_qaime is not None and musteri_col in df_qaime.columns:
            musteriler.extend(df_qaime[musteri_col].dropna().unique().tolist())
        if df_odenis is not None and musteri_col in df_odenis.columns:
            musteriler.extend(df_odenis[musteri_col].dropna().unique().tolist())
            
        musteriler = sorted(list(set(musteriler)))
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            secilmis_musteri = st.selectbox("Müştərini Seçin", musteriler)
        with col2:
            bas_tarix = st.date_input("Başlanğıc Tarixi", value=pd.to_datetime("2026-01-01"))
        with col3:
            bit_tarix = st.date_input("Bitiş Tarixi", value=pd.to_datetime("2026-12-31"))
            
        if st.button("🚀 Avtomatik Üzləşmə Aktı Yarat"):
            combined_rows = []
            
            # Qaimələri emal etmək (Debet)
            if df_qaime is not None and musteri_col in df_qaime.columns:
                q_df = df_qaime[df_qaime[musteri_col] == secilmis_musteri].copy()
                q_df[tarix_col] = pd.to_datetime(q_df[tarix_col], errors='coerce')
                q_df = q_df.dropna(subset=[tarix_col])
                
                for _, row in q_df.iterrows():
                    mblg = pd.to_numeric(row[mebleg_col], errors='coerce') or 0.0
                    snd = str(row[sened_col]) if pd.notna(row[sened_col]) else ""
                    combined_rows.append({
                        "Tarix": row[tarix_col],
                        "Növ": "Qaimə",
                        "Sənəd №": snd,
                        "Debet": mblg,
                        "Kredit": 0.0
                    })
            
            # Ödənişləri emal etmək (Kredit)
            if df_odenis is not None and musteri_col in df_odenis.columns:
                o_df = df_odenis[df_odenis[musteri_col] == secilmis_musteri].copy()
                o_df[tarix_col] = pd.to_datetime(o_df[tarix_col], errors='coerce')
                o_df = o_df.dropna(subset=[tarix_col])
                
                for _, row in o_df.iterrows():
                    mblg = pd.to_numeric(row[mebleg_col], errors='coerce') or 0.0
                    snd = str(row[sened_col]) if pd.notna(row[sened_col]) else ""
                    combined_rows.append({
                        "Tarix": row[tarix_col],
                        "Növ": "Ödəniş",
                        "Sənəd №": snd,
                        "Debet": 0.0,
                        "Kredit": mblg
                    })
                    
            if not combined_rows:
                st.warning("Seçilmiş müştəri üzrə heç bir əməliyyat tapılmadı.")
            else:
                full_df = pd.DataFrame(combined_rows).sort_values(by="Tarix")
                
                bas_tarix = pd.to_datetime(bas_tarix)
                bit_tarix = pd.to_datetime(bit_tarix)
                
                ilkin_df = full_df[full_df["Tarix"] < bas_tarix]
                ilkin_qaliq = ilkin_df["Debet"].sum() - ilkin_df["Kredit"].sum()
                
                dovr_df = full_df[(full_df["Tarix"] >= bas_tarix) & (full_df["Tarix"] <= bit_tarix)]
                
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
                        "Əməliyyat / Sənəd №": f"{row['Növ']} № {row['Sənəd №']}",
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
                
    except Exception as e:
        st.error(f"Xəta baş verdi: {e}")
else:
    st.info("Zəhmət olmasa sol tərəfdən Qaimə və ya Ödəniş faylını yükləyin.")
