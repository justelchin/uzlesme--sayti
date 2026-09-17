import streamlit as st
import pandas as pd

st.set_page_config(page_title="Üzləşmə Aktı Portalı", layout="wide")

st.title("📊 Debitor və Kreditor Üzləşmə Portalı")
st.write("Qaimə və Ödəniş fayllarını yükləyin, sütunları uyğunlaşdırın və avtomatik üzləşmə aktı hazırlayın.")

st.sidebar.header("📁 Faylları Yükləyin")
qaime_file = st.sidebar.file_uploader("1. Qaimələr (Satış/Alış) Faylı", type=["xlsx", "xls", "csv"])
odenis_file = st.sidebar.file_uploader("2. Ödənişlər (Bank/Kassa) Faylı", type=["xlsx", "xls", "csv"])

def load_clean_data(uploaded_file, is_qaime=False):
    if uploaded_file is None:
        return None
    
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None)
            
        header_row = None
        
        for i, row in df_raw.iterrows():
            row_vals = [str(val).strip().lower() for val in row.values if pd.notna(val)]
            row_str = " ".join(row_vals)
            
            if is_qaime:
                # Filtr sətrini keçmək üçün bir neçə sütun sözünü bir arada axtarırıq
                if ("tarix" in row_str or "çıxarış" in row_str) and ("məbləğ" in row_str or "status" in row_str or "alıcı" in row_str or "satıcı" in row_str or "vəziyyət" in row_str):
                    header_row = i
                    break
            else:
                if any(k in row_str for k in ["bank tərəfindən", "çıxarış", "silinmə", "daxil olma", "tarix"]):
                    header_row = i
                    break
                    
        if header_row is None:
            # Əgər şərt tapılmazsa, "Nəşr tarixi" və ya "Tarix" sözü olan ilk sətri götürək
            for i, row in df_raw.iterrows():
                row_str = " ".join([str(val).strip().lower() for val in row.values if pd.notna(val)])
                if "tarix" in row_str or "məbləğ" in row_str:
                    header_row = i
                    break
                    
        if header_row is None:
            header_row = 0

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
            st.subheader("📋 Qaimələr Faylı (Önizləmə)")
            st.dataframe(df_qaime.head(5))
    with col_p2:
        if df_odenis is not None:
            st.subheader("📋 Ödənişlər Faylı (Önizləmə)")
            st.dataframe(df_odenis.head(5))

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Sütun Uyğunlaşdırması")
    
    cols_qaime = df_qaime.columns.tolist() if df_qaime is not None else []
    cols_odenis = df_odenis.columns.tolist() if df_odenis is not None else []
    
    st.sidebar.markdown("**Qaimə Faylı Sütunları:**")
    tarix_q = st.sidebar.selectbox("Qaimə Tarix Sütunu", cols_qaime, key="t_q") if cols_qaime else None
    musteri_q = st.sidebar.selectbox("Qaimə Müştəri Adı Sütunu", cols_qaime, key="m_q") if cols_qaime else None
    mebleg_q = st.sidebar.selectbox("Qaimə Məbləğ Sütunu", cols_qaime, key="mb_q") if cols_qaime else None
    sened_q = st.sidebar.selectbox("Qaimə № Sütunu", cols_qaime, key="s_q") if cols_qaime else None
    
    st.sidebar.markdown("**Ödəniş Faylı Sütunları:**")
    tarix_o = st.sidebar.selectbox("Ödəniş Tarix Sütunu", cols_odenis, key="t_o") if cols_odenis else None
    musteri_o = st.sidebar.selectbox("Ödəniş Müştəri Adı Sütunu", cols_odenis, key="m_o") if cols_odenis else None
    mebleg_o = st.sidebar.selectbox("Ödəniş Məbləğ Sütunu", cols_odenis, key="mb_o") if cols_odenis else None
    sened_o = st.sidebar.selectbox("Ödəniş Sənəd/Açıqlama Sütunu", cols_odenis, key="s_o") if cols_odenis else None

    # Müştəri siyahısını toplamaq
    musteriler = set()
    if df_qaime is not None and musteri_q in df_qaime.columns:
        musteriler.update(df_qaime[musteri_q].dropna().astype(str).unique())
    if df_odenis is not None and musteri_o in df_odenis.columns:
        musteriler.update(df_odenis[musteri_o].dropna().astype(str).unique())
        
    musteriler_list = sorted([m for m in musteriler if m.strip() and not m.startswith("Unnamed") and m.lower() not in ["none", "nan", "status", "vəen"]])

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        secilmis_musteri = st.selectbox("Müştərini Seçin", musteriler_list if musteriler_list else ["Məlumat Tapılmadı"])
    with col2:
        bas_tarix = st.date_input("Başlanğıc Tarixi", value=pd.to_datetime("2026-01-01"))
    with col3:
        bit_tarix = st.date_input("Bitiş Tarixi", value=pd.to_datetime("2026-12-31"))
        
    if st.button("🚀 Avtomatik Üzləşmə Aktı Yarat"):
        combined_rows = []
        
        # Qaimələr (Debet)
        if df_qaime is not None and musteri_q:
            q_df = df_qaime[df_qaime[musteri_q].astype(str) == secilmis_musteri].copy()
            q_df[tarix_q] = pd.to_datetime(q_df[tarix_q], errors='coerce')
            q_df = q_df.dropna(subset=[tarix_q])
            
            for _, row in q_df.iterrows():
                mblg = pd.to_numeric(row[mebleg_q], errors='coerce') or 0.0
                snd = str(row[sened_q]) if pd.notna(row[sened_q]) else ""
                combined_rows.append({
                    "Tarix": row[tarix_q],
                    "Növ": "Qaimə",
                    "Sənəd №": snd,
                    "Debet": mblg,
                    "Kredit": 0.0
                })
        
        # Ödənişlər (Kredit)
        if df_odenis is not None and musteri_o:
            o_df = df_odenis[df_odenis[musteri_o].astype(str) == secilmis_musteri].copy()
            o_df[tarix_o] = pd.to_datetime(o_df[tarix_o], errors='coerce')
            o_df = o_df.dropna(subset=[tarix_o])
            
            for _, row in o_df.iterrows():
                mblg = pd.to_numeric(row[mebleg_o], errors='coerce') or 0.0
                snd = str(row[sened_o]) if pd.notna(row[sened_o]) else ""
                combined_rows.append({
                    "Tarix": row[tarix_o],
                    "Növ": "Ödəniş",
                    "Sənəd №": snd,
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

else:
    st.info("Zəhmət olmasa sol tərəfdən Qaimə və ya Ödəniş faylını yükləyin.")
