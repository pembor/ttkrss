import os, sys, time, json
from pathlib import Path
from datetime import datetime, timezone
import requests
from feedgen.feed import FeedGenerator

OUT_DIR = Path("feeds")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUBS_PATH = Path("subscriptions.csv")

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

def build_feed(username, videos):
    fg = FeedGenerator()
    fg.id(f"https://www.tiktok.com/@{username}")
    fg.title(f"TikTok – @{username}")
    fg.link(href=f"https://www.tiktok.com/@{username}", rel='alternate')
    fg.link(href=f"https://{os.getenv('GH_PAGES_HOST','example.com')}/feeds/{username}.xml", rel='self')
    fg.description(f"Posts públicos de @{username}")
    fg.language('pt-BR')

    for v in videos:
        vid_url = f"https://www.tiktok.com/@{username}/video/{v['id']}"
        fe = fg.add_entry()
        fe.id(vid_url)
        fe.link(href=vid_url)
        title = v.get('desc', 'Vídeo no TikTok').strip()
        if len(title) > 140:
            title = title[:137] + "..."
        fe.title(title)
        ts = v.get('createTime', int(time.time()))
        fe.published(datetime.fromtimestamp(int(ts), timezone.utc))
        cover = v.get('video', {}).get('cover', '')
        html = f"<p>{title}</p>"
        if cover:
            html += f'<p><img src="{cover}" alt="thumb"/></p>'
        fe.content(html, type='CDATA')
    return fg.rss_str(pretty=True)

def fetch_user_videos(username, limit=20):
    url = f"https://www.tiktok.com/@{username}?__a=1&__d=dis"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        )
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"@{username}: HTTP {r.status_code}")
            return []
        data = r.json()
        items = (
            data.get('props', {})
            .get('pageProps', {})
            .get('items', [])
        )
        return items[:limit]
    except Exception as e:
        print(f"@{username}: erro ao obter JSON ({e})")
        return []

def main():
    users = read_users()
    if not users:
        print("Nenhum usuário no subscriptions.csv")
        return

    for u in users:
        print(f"Coletando @{u} ...")
        videos = fetch_user_videos(u)
        if videos:
            xml = build_feed(u, videos)
            (OUT_DIR / f"{u}.xml").write_bytes(xml)
            print(f"✅ OK: feeds/{u}.xml ({len(videos)} vídeos)")
        else:
            print(f"⚠️ Nenhum vídeo encontrado para @{u}")
        time.sleep(2)

if __name__ == "__main__":
    main()
