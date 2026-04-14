import os
import glob
from app.debug_tools import debug_wrap

@debug_wrap

def find_latest_budget_file(folder: str):
    files = glob.glob(os.path.join(folder, "*.xlsx"))
    print("[DEBUG] Fichiers trouvés :", files)

    if not files:
        raise FileNotFoundError(f"Aucun fichier budget trouvé dans {folder}")

    latest = max(files, key=os.path.getmtime)
    print("[DEBUG] Fichier sélectionné :", latest)

    return latest



