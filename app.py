import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Üzləşmə Aktı Portalı", layout="wide")

st.title("📊 Debitor və Kreditor Üzləşmə Portalı")
st.write("Qaimə və Ödəniş fayllarını yükləyin, sütunları uyğunlaşdırın və avtomatik üzləşmə aktı hazırlayın.")

BIZIM_SIRKET = '"ŞƏKİ ŞƏRAB" MƏHDUD MƏSULİYYƏTLİ CƏMİYYƏTİ'

st.sidebar.header("📁 Faylları Yükləyin")
qaime_file = st.sidebar.file_uploader("1. Qaimələr (Satış/Alış) Faylı", type=["xlsx", "xls", "csv"])
odenis_file = st.sidebar.file_uploader("2. Ödənişlər (Bank/Kassa) Faylı", type=["xlsx", "xls", "csv"])

def normalize_text(text):
    if pd.isna(text):
        return ""
    text = str(text).upper()
    replacements = {
        'İ': 'I', 'Ə': 'E', 'Ğ': 'G', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U',
        '"': '', '”': '', '“': '', 'MƏHDUD MƏSULİYYƏTLİ CƏMİYYƏTİ': '', 
        'MMC': '', 'LLC': '', 'OOO': ''
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return re.sub(r'\s+', ' ', text).strip()

def get_core_name(text):
    norm = normalize_text(text)
    words = [w for w in norm.split() if len(w) >= 3 and w not in ['MƏHDUD', 'MƏSULİYYƏTLİ', 'CƏMİYYƏTİ', 'MMC', 'LLC']]
    return words[0] if words else norm

def clean_number(val):
    if pd.isna(val):
        return 0.0
    val_str = str(val).upper().replace("AZN", "").replace(" ", "").strip()
    if not val_str or val_str in ["NONE", "NAN"]:
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
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        if any("Unnamed" in str(col) for col in df.columns[:2]):
            for i in range(min(10, len(df))):
                row_vals = [str(v).lower() for v in df.iloc[i].values if pd.notna(v)]
                row_str = " ".join(row_vals)
                if ("tarix" in row_str or "çıxarış" in row_str or "kontragent" in row_str or "adı" in row_str):
                    df.columns = df.iloc[i].astype(str).str.strip()
                    df = df.iloc[i+1:].reset_index(drop=True)
                    break
                    
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
            st.dataframe(df_qaime.head(3))
    with col_p2:
        if df_odenis is not None:
            st.subheader("📋 Ödənişlər Faylı (Önizləmə)")
            st.dataframe(df_odenis.head(3))

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Sütun Uyğunlaşdırması")
    
    cols_qaime = df_qaime.columns.tolist() if df_qaime is not None else []
    cols_odenis = df_odenis.columns.tolist() if df_odenis is not None else []
    
    # Otomatik sütun təyini
    def find_default_col(cols, keywords):
        for c in cols:
            if any(k in c.lower() for k in keywords):
                return c
        return cols[0] if cols else None

    st.sidebar.markdown("**Qaimə Faylı Sütunları:**")
    tarix_q = st.sidebar.selectbox("Qaimə Tarix Sütunu", cols_qaime, index=cols_qaime.index(find_default_col(cols_qaime, ["tarix"])) if cols_qaime else 0, key="t_q") if cols_qaime else None
    musteri_q = st.sidebar.selectbox("Qaimə Müştəri Adı Sütunu", cols_qaime, index=cols_qaime.index(find_default_col(cols_qaime, ["adı", "müşterı", "alıcı"])) if cols_qaime else 0, key="m_q") if cols_qaime else None
    mebleg_q = st.sidebar.selectbox("Qaimə Məbləğ Sütunu", cols_qaime, index=cols_qaime.index(find_default_col(cols_qaime, ["yekun", "məbləğ"])) if cols_qaime else 0, key="mb_q") if cols_qaime else None
    sened_q = st.sidebar.selectbox("Qaimə № Sütunu", cols_qaime, index=cols_qaime.index(find_default_col(cols_qaime, ["nömr", "№"])) if cols_qaime else 0, key="s_q") if cols_qaime else None
    nov_q = st.sidebar.selectbox("Qaimə Növü Sütunu (İstəyə bağlı)", ["Seçilməyib"] + cols_qaime, index=0, key="n_q") if cols_qaime else "Seçilməyib"

    st.sidebar.markdown("**Ödəniş Faylı Sütunları:**")
    tarix_o = st.sidebar.selectbox("Ödəniş Tarix Sütunu", cols_odenis, index=cols_odenis.index(find_default_col(cols_odenis, ["keçirilib", "tarix"])) if cols_odenis else 0, key="t_o") if cols_odenis else None
    musteri_o = st.sidebar.selectbox("Ödəniş Müştəri Adı Sütunu", cols_odenis, index=cols_odenis.index(find_default_col(cols_odenis, ["kontragent", "ödəyən"])) if cols_odenis else 0, key="m_o") if cols_odenis else None
    mebleg_o = st.sidebar.selectbox("Ödəniş Məbləğ Sütunu", cols_odenis, index=cols_odenis.index(find_default_col(cols_odenis, ["silinmə", "daxil"])) if cols_odenis else 0, key="mb_o") if cols_odenis else None
    sened_o = st.sidebar.selectbox("Ödəniş Sənəd/Açıqlama Sütunu", cols_odenis, index=cols_odenis.index(find_default_col(cols_odenis, ["təyinat", "açıqlama"])) if cols_odenis else 0, key="s_o") if cols_odenis else None

    # Müştəri siyahısı
    musteriler_list = []
    if df_qaime is not None and musteri_q in df_qaime.columns:
        raw_m = df_qaime[musteri_q].dropna().astype(str).unique().tolist()
        for m in raw_m:
            m_clean = m.strip()
            if m_clean and not m_clean.replace('.', '').isdigit() and not m_clean.startswith("Unnamed") and m_clean.lower() not in ["none", "nan", "adı", "status", "vəen"]:
                musteriler_list.append(m_clean)
        musteriler_list = sorted(list(set(musteriler_list)))

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        secilmis_musteri = st.selectbox(
            "Müştərini Seçin (Adı yazaraq axtara bilərsiniz)", 
            options=musteriler_list if musteriler_list else ["Məlumat Tapılmadı"]
        )
    with col2:
        bas_tarix = st.date_input("Başlanğıc Tarixi", value=pd.to_datetime("2023-01-01"))
    with col3:
        bit_tarix = st.date_input("Bitiş Tarixi", value=pd.to_datetime("2026-12-31"))
        
    if st.button("🚀 Avtomatik Üzləşmə Aktı Yarat"):
        combined_rows = []
        target_raw = str(secilmis_musteri).strip()
        target_core = get_core_name(secilmis_musteri)
        
        # 1. Qaimələr (Debet)
        if df_qaime is not None and musteri_q and tarix_q:
            for _, row in df_qaime.iterrows():
                val_raw = str(row[musteri_q]).strip()
                val_core = get_core_name(row[musteri_q])
                
                if (val_raw == target_raw) or (target_core == val_core):
                    mblg = clean_number(row[mebleg_q]) if mebleg_q else 0.0
                    snd = str(row[sened_q]).strip() if sened_q and pd.notna(row[sened_q]) else ""
                    
                    # Qaimə növünü əldə etmək
                    q_type_str = ""
                    if nov_q != "Seçilməyib" and nov_q in row and pd.notna(row[nov_q]):
                        q_type_str = f" ({str(row[nov_q]).strip()})"
                        
                    raw_date = row[tarix_q]
                    dt_val = pd.to_datetime(raw_date, dayfirst=True, errors='coerce')
                    
                    combined_rows.append({
                        "Tarix": dt_val if pd.notna(dt_val) else pd.to_datetime("2026-01-01"),
                        "Tarix_Str": str(raw_date)[:10] if pd.notna(raw_date) else "-",
                        "Növ": "Qaimə",
                        "Sənəd №": f"{snd}{q_type_str}",
                        "Debet": mblg,
                        "Kredit": 0.0
                    })
        
        # 2. Ödənişlər (Kredit)
        if df_odenis is not None and musteri_o and tarix_o:
            for _, row in df_odenis.iterrows():
                val_m = get_core_name(row[musteri_o])
                val_s = get_core_name(row[sened_o]) if sened_o and sened_o in row else ""
                
                if target_core and (target_core in val_m or target_core in val_s):
                    mblg = clean_number(row[mebleg_o]) if mebleg_o else 0.0
                    snd = str(row[sened_o]) if sened_o and pd.notna(row[sened_o]) else "Ödəniş"
                    raw_date = row[tarix_o]
                    dt_val = pd.to_datetime(raw_date, dayfirst=True, errors='coerce')
                    
                    combined_rows.append({
                        "Tarix": dt_val if pd.notna(dt_val) else pd.to_datetime("2026-01-01"),
                        "Tarix_Str": str(raw_date)[:10] if pd.notna(raw_date) else "-",
                        "Növ": "Ödəniş",
                        "Sənəd №": snd[:40],
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
            
            # 1. İlkin Qalıq Sətri
            akt_rows = [{
                "Tarix": "-",
                "Əməliyyat / Sənəd №": "Dövrə qədər olan ilkin qalıq",
                "Debet (Borc)": f"{ilkin_qaliq:,.2f}" if ilkin_qaliq > 0 else "-",
                "Kredit (Alacaq)": f"{abs(ilkin_qaliq):,.2f}" if ilkin_qaliq < 0 else "-"
            }]
            
            # 2. Dövr Əməliyyatları
            for _, row in dovr_df.iterrows():
                debet = row["Debet"]
                kredit = row["Kredit"]
                t_display = row["Tarix"].strftime("%d.%m.%Y") if pd.notna(row["Tarix"]) else row["Tarix_Str"]
                
                akt_rows.append({
                    "Tarix": t_display,
                    "Əməliyyat / Sənəd №": f"{row['Növ']} № {row['Sənəd №']}",
                    "Debet (Borc)": f"{debet:,.2f}" if debet > 0 else "-",
                    "Kredit (Alacaq)": f"{kredit:,.2f}" if kredit > 0 else "-"
                })
            
            # 3. Yekun Son Qalıq Sətri
            dovr_debet = dovr_df["Debet"].sum()
            dovr_kredit = dovr_df["Kredit"].sum()
            son_qaliq = ilkin_qaliq + dovr_debet - dovr_kredit
            
            akt_rows.append({
                "Tarix": "-",
                "Əməliyyat / Sənəd №": "📌 DÖVRÜN SONUNA OLAN YEKUN QALIQ",
                "Debet (Borc)": f"{son_qaliq:,.2f}" if son_qaliq > 0 else "-",
                "Kredit (Alacaq)": f"{abs(son_qaliq):,.2f}" if son_qaliq < 0 else "-"
            })
                
            res_df = pd.DataFrame(akt_rows)
            
            st.markdown("---")
            st.markdown("## 📑 CARİ HESABLARIN ÜZLƏŞDİRİLMƏSİ AKTI")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.markdown(f"**Tərəf 1 (Biz):**  \n{BIZIM_SIRKET}")
            with col_b2:
                st.markdown(f"**Tərəf 2 (Qarşı Tərəf):**  \n{secilmis_musteri}")
                
            st.markdown(f"**Əhatə etdiyi dövr:** {bas_tarix_dt.strftime('%d.%m.%Y')} — {bit_tarix_dt.strftime('%d.%m.%Y')}")
            st.markdown("---")
            
            st.table(res_df)
            
            st.markdown("---")
            st.markdown("### Tərəflərin İmzaları:")
            col_i1, col_i2 = st.columns(2)
            with col_i1:
                st.markdown(f"**{BIZIM_SIRKET}**  \n\nBaş mühasib / Məsul şəxs: _______________  \n*(İmza və M.Y.)*")
            with col_i2:
                st.markdown(f"**{secilmis_musteri}**  \n\nBaş mühasib / Məsul şəxs: _______________  \n*(İmza və M.Y.)*")
            
            csv_data = res_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Üzləşmə Aktını Yüklə (CSV/Excel)",
                data=csv_data,
                file_name=f"Uzlesme_Akti_{secilmis_musteri}.csv",
                mime="text/csv"
            )

else:
    st.info("Zəhmət olmasa sol tərəfdən Qaimə və ya Ödəniş faylını yükləyin.")
