import os, sys, time
from pathlib import Path
import requests

OUT_DIR = Path("feeds")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUBS_PATH = Path("subscriptions.csv")

# Você pode listar múltiplas bases separadas por vírgula em RSSHUB_BASES
# Ex.: RSSHUB_BASES="https://seu-worker.workers.dev,https://rsshub.app"
def get_bases():
    env = os.getenv("RSSHUB_BASES") or os.getenv("RSSHUB_BASE") or "https://rsshub.app"
    bases = [b.strip().rstrip("/") for b in env.split(",") if b.strip()]
    return bases

def read_users():
    users = []
    if not SUBS_PATH.exists():
        print("subscriptions.csv não encontrado.", file=sys.stderr)
        return users
    with SUBS_PATH.open("r", encoding="utf-8") as f:
        for raw in f:
            u = raw.strip().lstrip("@").rstrip(",")
            if u:
                users.append(u)
    return users

def fetch_and_save_one(base, username, timeout=20):
    url = f"{base}/tiktok/user/{username}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    if r.status_code == 200 and r.text.lstrip().startswith("<?xml"):
        (OUT_DIR / f"{username}.xml").write_text(r.text, encoding="utf-8")
        print(f"✅ OK @{username} via {base}")
        return True, None
    return False, f"HTTP {r.status_code} (base {base})"

def fetch_with_fallback(username, retries=3, sleep_base=2):
    bases = get_bases()
    attempt = 0
    last_err = None
    for _ in range(retries):
        for base in bases:
            attempt += 1
            try:
                print(f"Baixando @{username} de {base} (tentativa {attempt})")
                ok, err = fetch_and_save_one(base, username)
                if ok:
                    return True
                else:
                    print(f"Falhou @{username}: {err}")
            except Exception as e:
                last_err = str(e)
                print(f"Erro @{username} em {base}: {e}")
            # pequeno backoff entre bases
            time.sleep(1)
        # backoff entre rodadas
        time.sleep(sleep_base * attempt)
    print(f"⚠️ Falhei com @{username} após {attempt} tentativas. Último erro: {last_err}")
    return False

def main():
    users = read_users()
    if not users:
        print("Nenhum usuário no subscriptions.csv")
        return
    for u in users:
        fetch_with_fallback(u)

if __name__ == "__main__":
    main()
