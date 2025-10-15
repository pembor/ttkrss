import csv, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from feedgen.feed import FeedGenerator
from tiktokapipy.api import TikTokAPI  # lib moderna (não é a antiga TikTokApi)

OUT_DIR = Path("feeds")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUBS_PATH = Path("subscriptions.csv")

RETRIES = 3
NAV_TIMEOUT = 60.0  # segundos

def read_users():
    users = []
    if not SUBS_PATH.exists():
        print("subscriptions.csv não encontrado na raiz", file=sys.stderr)
        return users
    with SUBS_PATH.open("r", encoding="utf-8") as f:
        for raw in f:
            u = raw.strip().lstrip("@").rstrip(",")
            if u:
                users.append(u)
    return users

def iso8601(dt):
    if isinstance(dt, str):
        return dt
    return dt.replace(tzinfo=timezone.utc).isoformat()

def build_feed(username, videos):
    fg = FeedGenerator()
    fg.id(f"https://www.tiktok.com/@{username}")
    fg.title(f"TikTok – @{username}")
    fg.link(href=f"https://www.tiktok.com/@{username}", rel='alternate')
    fg.link(href=f"https://{os.getenv('GH_PAGES_HOST','example.com')}/feeds/{username}.xml", rel='self')
    fg.description(f"Posts públicos de @{username} (gerado automaticamente)")
    fg.language('pt-BR')

    for v in videos:
        fe = fg.add_entry()
        vid_url = f"https://www.tiktok.com/@{username}/video/{v.id}"
        fe.id(vid_url)
        fe.link(href=vid_url)
        title = (v.desc or "Vídeo no TikTok").strip()
        if len(title) > 140:
            title = title[:137] + "..."
        fe.title(title or f"Vídeo {v.id}")
        try:
            fe.published(iso8601(v.create_time))
        except Exception:
            fe.published(datetime.now(timezone.utc))
        thumb = getattr(v, "video", None)
        cover = getattr(thumb, "cover", None) if thumb else None
        cover_url = getattr(cover, "url_list", [None])[0] if cover else None
        html = f"<p>{title}</p>"
        if cover_url:
            html += f'<p><img src="{cover_url}" alt="thumb"/></p>'
        fe.content(html, type='CDATA')
    return fg.rss_str(pretty=True)

def fetch_user_videos(api, unique_id, limit=15):
    user = api.user(unique_id)  # passa sem 'username='
    out = []
    for i, v in enumerate(user.videos):
        out.append(v)
        if i + 1 >= limit:
            break
    return out

def main():
    users = read_users()
    if not users:
        print("subscriptions.csv está vazio.")
        return

    for attempt in range(1, RETRIES + 1):
        try:
            print(f">>> abrindo TikTokAPI (tentativa {attempt}/{RETRIES}) com timeout {NAV_TIMEOUT}s")
            with TikTokAPI(navigation_timeout=NAV_TIMEOUT) as api:
                for u in users:
                    try:
                        print(f"Coletando @{u} ...")
                        vids = fetch_user_videos(api, u, limit=20)
                        xml = build_feed(u, vids)
                        (OUT_DIR / f"{u}.xml").write_bytes(xml)
                        print(f"OK: feeds/{u}.xml ({len(vids)} vídeos)")
                    except Exception as e:
                        print(f"ERRO @{u}: {e}")
                return
        except Exception as e:
            print(f"[API/Browser] falhou (tentativa {attempt}/{RETRIES}): {e}")
            if attempt < RETRIES:
                time.sleep(5 * attempt)
            else:
                print("Desisti após várias tentativas.")

if __name__ == "__main__":
    main()
