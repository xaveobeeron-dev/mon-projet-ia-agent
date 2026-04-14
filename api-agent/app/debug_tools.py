import traceback
import datetime

def debug_wrap(func):
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        print(f"[DEBUG] → Appel fonction : {func_name}")
        print(f"[DEBUG] → Args : {args}")
        print(f"[DEBUG] → Kwargs : {kwargs}")

        try:
            result = func(*args, **kwargs)
            print(f"[DEBUG] ← Retour fonction : {func_name} OK")
            return result

        except Exception as e:
            print(f"[ERROR] Exception dans {func_name} : {e}")

            # Sauvegarde dans un fichier
            with open("/data-agent/debug_errors.log", "a", encoding="utf-8") as f:
                f.write("\n" + "="*80 + "\n")
                f.write(f"DATE : {datetime.datetime.now()}\n")
                f.write(f"FONCTION : {func_name}\n")
                f.write(f"ARGS : {args}\n")
                f.write(f"KWARGS : {kwargs}\n")
                f.write(f"ERREUR : {e}\n")
                f.write("STACKTRACE :\n")
                f.write(traceback.format_exc())
                f.write("\n" + "="*80 + "\n")

            raise
    return wrapper
