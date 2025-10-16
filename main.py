import os, sys, time
from pathlib import Path
import requests

OUT_DIR = Path("feeds")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUBS_PATH = Path("subscriptions.csv")

# Base do RSSHub (pode trocar por outra instância pública ou sua própria)
RSSHUB_BASE = os.getenv("RSSHUB_BASE", "https://rsshub.app").rstrip("/")

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

def fetch_and_save(username, retries=3, timeout=20):
    url = f"{RSSHUB_BASE}/tiktok/user/{username}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        )
    }
    for attempt in range(1, retries + 1):
        try:
            print(f"Baixando RSS @{username} ({url}) tentativa {attempt}/{retries}")
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200 and r.text.strip().startswith("<?xml"):
                (OUT_DIR / f"{username}.xml").write_text(r.text, encoding="utf-8")
                print(f"✅ OK: feeds/{username}.xml")
                return True
            else:
                print(f"HTTP {r.status_code} / conteúdo não-XML para @{username}")
        except Exception as e:
            print(f"@{username}: erro {e}")
        time.sleep(2 * attempt)
    print(f"⚠️ Falhei com @{username} após {retries} tentativas")
    return False

def main():
    users = read_users()
    if not users:
        print("Nenhum usuário no subscriptions.csv")
        return
    for u in users:
        fetch_and_save(u)

if __name__ == "__main__":
    main()
