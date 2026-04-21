import requests
from bs4 import BeautifulSoup
import datetime
import os
import re
import json
import urllib.parse
from datetime import timedelta, timezone

# --- 設定 ---
HISTORY_FILE = "CHUSPO_history.txt"
STOCK_FILE = "CHUSPO_stock.json"

def build_summary(title):
    # 余計な装飾をカット
    text = re.sub(r'\(.*?\)|（.*?）|【.*?】', '', title).strip()
    # ハッシュタグを #dragons #中日ドラゴンズ に変更
    return f"{text}\n\n#dragons #中日ドラゴンズ"

def get_chuspo_news():
    url = "https://www.chunichi.co.jp/chuspo/dragons"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = [line.strip() for line in f.readlines()]

    stock = []
    if os.path.exists(STOCK_FILE):
        try:
            with open(STOCK_FILE, "r", encoding="utf-8") as f:
                stock = json.load(f)
        except:
            stock = []

    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')

        all_links = soup.find_all('a', href=True)
        new_entries_for_history = []
        seen_hrefs = set()

        for a in all_links:
            href = a.get('href')
            if not re.search(r'/article/\d{6,}', href):
                continue
                
            full_url = urllib.parse.urljoin(url, href)
            if full_url in seen_hrefs: continue
            
            title = a.get_text().strip()
            if len(title) < 20: 
                continue

            if title not in history and full_url not in history:
                summary_text = build_summary(title)
                stock.insert(0, {"summary": summary_text, "url": full_url})
                new_entries_for_history.extend([title, full_url])
                history.extend([title, full_url])
                seen_hrefs.add(full_url)

        if new_entries_for_history:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                for entry in new_entries_for_history: f.write(entry + "\n")
        
        stock = stock[:30]
        with open(STOCK_FILE, "w", encoding="utf-8") as f:
            json.dump(stock, f, ensure_ascii=False, indent=4)
                
    except Exception as e:
        print(f"Error: {e}")
    
    return stock

def create_html(news_list):
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.datetime.now(JST).strftime('%m/%d %H:%M')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>中スポ ドラゴンズ速報</title>
        <style>
            body {{ font-family: sans-serif; background: #f0f4f8; padding: 10px; margin: 0; }}
            .header {{ 
                background:#0044cc; color:white; padding:15px; text-align:center; 
                position: sticky; top: 0; z-index: 1000; border-bottom: 3px solid #ffcc00;
                display: flex; justify-content: space-between; align-items: center;
            }}
            .refresh-btn {{ 
                background: #ffcc00; color: #0044cc; border: none; padding: 8px 12px; 
                border-radius: 20px; font-weight: bold; cursor: pointer; text-decoration: none; font-size: 14px;
            }}
            .card {{ 
                background: white; border-radius: 12px; padding: 18px; margin-bottom: 15px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.05); position: relative;
            }}
            .close-btn {{ 
                position: absolute; top: 10px; right: 10px; color: #ccc; 
                font-size: 24px; cursor: pointer; border: none; background: none; width: 40px; height: 40px;
            }}
            .summary-text {{ font-weight: bold; font-size: 1.1em; margin-bottom: 15px; line-height: 1.5; color: #1a1a1a; padding-right: 30px; }}
            .btn-group {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
            .btn {{ text-align: center; text-decoration: none; padding: 12px; border-radius: 8px; font-weight: bold; }}
            .read-btn {{ background: #e7efff; color: #0044cc; }}
            .post-btn {{ background: #1d9bf0; color: white; }}
        </style>
        <script>
            function removeCard(btn) {{
                const card = btn.closest('.card');
                card.remove();
            }}
            function reloadPage() {{
                location.reload();
            }}
        </script>
    </head>
    <body>
        <div class="header">
            <div style="font-weight:bold;">🐉 中スポ ({now})</div>
            <button onclick="reloadPage()" class="refresh-btn">🔄 更新</button>
        </div>
        <div style="margin-top:15px;">
    """
    for item in news_list:
        tweet_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(item['summary'] + chr(10) + item['url'])}"
        html_content += f"""
            <div class="card">
                <button class="close-btn" onclick="removeCard(this)">✕</button>
                <div class="summary-text">{item['summary']}</div>
                <div class="btn-group">
                    <a href="{item['url']}" target="_blank" class="btn read-btn">📰 読む</a>
                    <a href="{tweet_url}" target="_blank" class="btn post-btn" onclick="removeCard(this)">𝕏 ポスト</a>
                </div>
            </div>
        """
    if not news_list:
        html_content += "<p style='text-align:center; padding:50px; color:#666;'>新着ニュースはありません。</p>"
    html_content += "</div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    news = get_chuspo_news()
    create_html(news)
