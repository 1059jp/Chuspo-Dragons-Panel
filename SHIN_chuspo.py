import requests
from bs4 import BeautifulSoup
import datetime
import os
import re
from datetime import timedelta, timezone
import json
import urllib.parse

# --- 設定 ---
HISTORY_FILE = "CHUSPO_history.txt"
STOCK_FILE = "CHUSPO_stock.json"

def build_summary(title):
    # 余計な記号を消してスッキリさせる
    text = re.sub(r'\(.*?\)|（.*?）|【.*?】', '', title).strip()
    return f"{text}\n\n#dragons #中日スポーツ"

def get_chuspo_news():
    url = "https://www.chunichi.co.jp/chuspo/dragons"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = [line.strip() for line in f.readlines()]

    stock = []
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.encoding = res.apparent_encoding # 文字化け防止
        soup = BeautifulSoup(res.text, 'html.parser')

        # 中日スポーツのニュース一覧の塊を探す
        items = soup.select('.news-list-item, .item') 

        new_entries = []
        for item in items:
            link_tag = item.find('a')
            if not link_tag: continue
            
            href = urllib.parse.urljoin(url, link_tag.get('href', ''))
            title_tag = item.find(['h2', 'h3', 'p', 'span'], class_=re.compile(r'title|text'))
            title = title_tag.get_text().strip() if title_tag else link_tag.get_text().strip()

            if len(title) < 10: continue

            if title not in history and href not in history:
                summary_text = build_summary(title)
                stock.insert(0, {"summary": summary_text, "url": href})
                new_entries.extend([title, href])
                history.extend([title, href])

        if new_entries:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                for entry in new_entries: f.write(entry + "\n")
                
    except Exception as e:
        print(f"Error: {e}")
    
    stock = stock[:20]
    with open(STOCK_FILE, "w", encoding="utf-8") as f:
        json.dump(stock, f, ensure_ascii=False, indent=4)
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
            body {{ font-family: sans-serif; background: #eef2f7; padding: 10px; margin: 0; }}
            .header {{ background:#0044cc; color:white; padding:15px; text-align:center; position: sticky; top: 0; z-index: 1000; }}
            .card {{ background: white; border-radius: 10px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-left: 5px solid #0044cc; }}
            .summary-text {{ font-weight: bold; margin-bottom: 15px; line-height: 1.4; }}
            .btn-group {{ display: flex; gap: 8px; }}
            .btn {{ flex: 1; text-align: center; text-decoration: none; padding: 12px; border-radius: 5px; font-weight: bold; font-size: 0.9em; }}
            .read-btn {{ background: #f0f2f5; color: #0044cc; border: 1px solid #0044cc; }}
            .post-btn {{ background: #1d9bf0; color: white; }}
        </style>
    </head>
    <body>
        <div class="header"><h2>📰 中スポ速報 ({now})</h2></div>
    """
    for item in news_list:
        tweet_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(item['summary'] + chr(10) + item['url'])}"
        html_content += f"""
            <div class="card">
                <div class="summary-text">{item['summary']}</div>
                <div class="btn-group">
                    <a href="{item['url']}" target="_blank" class="btn read-btn">📰 読む</a>
                    <a href="{tweet_url}" target="_blank" class="btn post-btn">𝕏 ポスト</a>
                </div>
            </div>
        """
    if not news_list:
        html_content += "<p style='text-align:center; padding:50px; color:#666;'>新着ニュースはありません。</p>"
    html_content += "</body></html>"
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    news = get_chuspo_news()
    create_html(news)
