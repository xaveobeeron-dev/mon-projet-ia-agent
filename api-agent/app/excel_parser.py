import pandas as pd
from app.debug_tools import debug_wrap

@debug_wrap
def parse_excel(excel_path: str) -> dict:
    print(f"[DEBUG] Lecture Excel : {excel_path}")

    df = pd.read_excel(excel_path)

    # Normalisation des noms de colonnes
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Détection automatique
    def find_col(df, names):
        for name in names:
            for col in df.columns:
                if name in col:
                    return col
        return None

    col_prevu = find_col(df, ["prevu", "prévu"])
    col_realise = find_col(df, ["realise", "réalisé"])
    col_ecart = find_col(df, ["ecart", "écart"])
    col_week = find_col(df, ["semaine", "sem"])

    if not col_prevu or not col_realise:
        raise ValueError("Colonnes prévues/réalisées introuvables dans l'Excel.")

    # 🔥 Nettoyage ultra robuste des nombres
    def clean_number(x):
        if isinstance(x, str):
            x = x.replace("€", "")
            x = x.replace(" ", "")
            x = x.replace("\u00A0", "")   # espace insécable normal
            x = x.replace("\u202F", "")   # espace insécable fin (ton cas)
            x = x.replace(",", ".")
            x = x.strip()
        return pd.to_numeric(x, errors="coerce")

    df[col_prevu] = df[col_prevu].apply(clean_number).fillna(0)
    df[col_realise] = df[col_realise].apply(clean_number).fillna(0)

    # Si l'écart existe déjà dans l'Excel, on le nettoie aussi
    if col_ecart:
        df[col_ecart] = df[col_ecart].apply(clean_number).fillna(0)

    # Calcul des cumuls
    df["prevu_cumule"] = df[col_prevu].cumsum()
    df["realise_cumule"] = df[col_realise].cumsum()
    df["ecart_cumule"] = df["realise_cumule"] - df["prevu_cumule"]

    context = {
        "semaines": df[col_week].tolist() if col_week else [],
        "prevu_cumule": df["prevu_cumule"].tolist(),
        "realise_cumule": df["realise_cumule"].tolist(),
        "ecart_cumule": df["ecart_cumule"].tolist(),
    }

    return context
