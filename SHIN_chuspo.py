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
    # タイトルをきれいにする
    text = re.sub(r'\(.*?\)|（.*?）|【.*?】', '', title).strip()
    return f"{text}\n\n#dragons #中日スポーツ"

def get_chuspo_news():
    # ドラゴンズニュースのトップページ
    url = "https://www.chunichi.co.jp/chuspo/dragons"
    # スマホからのアクセスを装ってブロックを回避
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
    }

    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = [line.strip() for line in f.readlines()]

    stock = []
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')

        # 中日スポーツの記事リンクを直接狙い撃ちします
        # リンクの中に "/chuspo/article/dragons/" が含まれるものをすべて抽出
        items = soup.find_all('a', href=re.compile(r'/chuspo/article/dragons/'))

        new_entries = []
        seen_hrefs = set() # 同じニュースを2回拾わないためのチェック

        for item in items:
            href = urllib.parse.urljoin(url, item.get('href', ''))
            if href in seen_hrefs: continue
            
            # 見出しテキストを取得
            title = item.get_text().strip()
            # 15文字以下の短いゴミデータや「一覧へ」などを除外
            if len(title) < 15: continue 

            if title not in history and href not in history:
                summary_text = build_summary(title)
                stock.insert(0, {"summary": summary_text, "url": href})
                new_entries.extend([title, href])
                history.extend([title, href])
                seen_hrefs.add(href)

        if new_entries:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                for entry in new_entries: f.write(entry + "\n")
                
    except Exception as e:
        print(f"Error: {e}")
    
    return stock[:20]

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
            .header {{ background:#0044cc; color:white; padding:15px; text-align:center; position: sticky; top: 0; z-index: 1000; border-radius: 0 0 15px 15px; }}
            .card {{ background: white; border-radius: 12px; padding: 18px; margin: 12px 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-left: 6px solid #0044cc; }}
            .summary-text {{ font-weight: bold; margin-bottom: 15px; line-height: 1.5; color: #333; }}
            .btn-group {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
            .btn {{ text-align: center; text-decoration: none; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 0.95em; }}
            .read-btn {{ background: #f0f2f5; color: #0044cc; border: 1px solid #0044cc; }}
            .post-btn {{ background: #1d9bf0; color: white; }}
        </style>
    </head>
    <body>
        <div class="header"><h2 style="margin:0;">🐉 中スポ速報 ({now})</h2></div>
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
        html_content += "<p style='text-align:center; padding:50px; color:#666;'>新着ニュースはありません。<br>時間をおいて更新してください。</p>"
    html_content += "</body></html>"
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    news = get_chuspo_news()
    create_html(news)
