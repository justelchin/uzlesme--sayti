import pandas as pd

# Tutaq ki, məlumatlarınız DataFrame-dədir və hər kontragent üzrə qaimə və ödəniş cəmləri hesablanıb:
# total_invoice = qaimələrin cəmi (Debet)
# total_payment = ödənişlərin cəmi (Kredit)

def calculate_balance_side(row):
    invoice_sum = row['Qaime_Cemi']  # Qaimələrin ümumi məbləği
    payment_sum = row['Odenis_Cemi']  # Ödənişlərin ümumi məbləği
    diff = abs(invoice_sum - payment_sum)

    if invoice_sum > payment_sum:
        return pd.Series(
            [diff, 0.0, 'Kreditor (Borclu)'],
            index=['Kreditor_Qaliqi', 'Debitor_Qaliqi', 'Status'],
        )
    elif payment_sum > invoice_sum:
        return pd.Series(
            [0.0, diff, 'Debitor (Artıq ödəniş)'],
            index=['Kreditor_Qaliqi', 'Debitor_Qaliqi', 'Status'],
        )
    else:
        return pd.Series(
            [0.0, 0.0, 'Sıfır balans'],
            index=['Kreditor_Qaliqi', 'Debitor_Qaliqi', 'Status'],
        )


# Cədvələ tətbiq etmək üçün:
# df[['Kreditor_Qaliqi', 'Debitor_Qaliqi', 'Status']] = df.apply(calculate_balance_side, axis=1)
