import streamlit as st
import pandas as pd

st.set_page_config(page_title="Üzləşmə Aktı Portalı", layout="wide")

st.title("📊 Debitor və Kreditor Üzləşmə Portalı")
st.write("Excel faylını yükləyin və avtomatik üzləşmə aktı hazırlayın.")

uploaded_file = st.sidebar.file_uploader("Excel / CSV Faylını Seçin", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None)
            
        header_row = 0
        for i, row in df_raw.iterrows():
            row_str = " ".join([str(val).lower() for val in row.values if pd.notna(val)])
            if any(k in row_str for k in ["tarix", "№", "status", "qaimə", "məbləğ", "müştəri", "alınma"]):
                header_row = i
                break
                
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, skiprows=header_row)
        else:
            df = pd.read_excel(uploaded_file, skiprows=header_row)
            
        st.sidebar.success("Fayl uğurla yükləndi!")
        
        st.subheader("📋 Yüklənmiş Məlumatların Önizləməsi")
        st.dataframe(df.head(5))
        
        cols = [str(c) for c in df.columns.tolist()]
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("Sütun İnteqrasiyası")
        
        tarix_col = st.sidebar.selectbox("Tarix Sütunu", cols)
        musteri_col = st.sidebar.selectbox("Müştəri Adı Sütunu", cols)
        nov_col = st.sidebar.selectbox("Əməliyyat Növü (Qaimə/Ödəniş) Sütunu", cols)
        mebleg_col = st.sidebar.selectbox("Məbləğ Sütunu", cols)
        sened_col = st.sidebar.selectbox("Sənəd № Sütunu", cols)
        
        musteriler = df[musteri_col].dropna().unique().tolist()
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            secilmis_musteri = st.selectbox("Müştərini Seçin", musteriler)
        with col2:
            bas_tarix = st.date_input("Başlanğıc Tarixi", value=pd.to_datetime(df[tarix_col], errors='coerce').min())
        with col3:
            bit_tarix = st.date_input("Bitiş Tarixi", value=pd.to_datetime(df[tarix_col], errors='coerce').max())
            
        if st.button("🚀 Üzləşmə Aktını Generasiya Et"):
            df[tarix_col] = pd.to_datetime(df[tarix_col], errors='coerce')
            df = df.dropna(subset=[tarix_col])
            
            bas_tarix = pd.to_datetime(bas_tarix)
            bit_tarix = pd.to_datetime(bit_tarix)
            
            m_df = df[df[musteri_col] == secilmis_musteri].sort_values(by=tarix_col)
            
            ilkin_df = m_df[m_df[tarix_col] < bas_tarix]
            
            ilkin_debet = pd.to_numeric(ilkin_df[ilkin_df[nov_col].astype(str).str.contains("Qaimə|Debet|Satış", case=False, na=False)][mebleg_col], errors='coerce').sum()
            ilkin_kredit = pd.to_numeric(ilkin_df[ilkin_df[nov_col].astype(str).str.contains("Ödəniş|Kredit|Alış", case=False, na=False)][mebleg_col], errors='coerce').sum()
            ilkin_qaliq = ilkin_debet - ilkin_kredit
            
            dovr_df = m_df[(m_df[tarix_col] >= bas_tarix) & (m_df[tarix_col] <= bit_tarix)].copy()
            
            akt_rows = [{
                "Tarix": "-",
                "Əməliyyat / Sənəd №": "Dövrə qədər olan ilkin qalıq",
                "Debet (Borc)": "-",
                "Kredit (Alacaq)": "-",
                "Qalıq": ilkin_qaliq
            }]
            
            cari_qaliq = ilkin_qaliq
            for idx, row in dovr_df.iterrows():
                nov = str(row[nov_col]) if pd.notna(row[nov_col]) else ""
                
                try:
                    mebleg = float(row[mebleg_col]) if pd.notna(row[mebleg_col]) else 0.0
                except:
                    mebleg = 0.0
                    
                sened = str(row[sened_col]) if pd.notna(row[sened_col]) else ""
                t_str = row[tarix_col].strftime("%d.%m.%Y")
                
                if any(k in nov.lower() for k in ["qaimə", "debet", "satış", "alış"]):
                    debet = mebleg
                    kredit = 0
                else:
                    debet = 0
                    kredit = mebleg
                    
                cari_qaliq += (debet - kredit)
                
                akt_rows.append({
                    "Tarix": t_str,
                    "Əməliyyat / Sənəd №": f"{nov} № {sened}",
                    "Debet (Borc)": debet if debet > 0 else "-",
                    "Kredit (Alacaq)": kredit if kredit > 0 else "-",
                    "Qalıq": cari_qaliq
                })
                
            res_df = pd.DataFrame(akt_rows)
            
            st.markdown(f"### 📑 {secilmis_musteri} üzrə Üzləşmə Aktı")
            st.table(res_df)
            
            csv_data = res_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Üzləşmə Aktını İdxal Et (CSV/Excel)",
                data=csv_data,
                file_name=f"Uzlesme_Akti_{secilmis_musteri}.csv",
                mime="text/csv"
            )
            
    except Exception as e:
        st.error(f"Xəta baş verdi: {e}")
else:
    st.info("Zəhmət olmasa sol tərəfdən Excel və ya CSV faylınızı yükləyin.")
