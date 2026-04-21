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
    # 余計な文字を掃除
    text = re.sub(r'\(.*?\)|（.*?）|【.*?】', '', title).strip()
    return f"{text}\n\n#dragons #中日スポーツ"

def get_chuspo_news():
    url = "https://www.chunichi.co.jp/chuspo/dragons"
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

        # --- 【修正ポイント】ニュース記事の「塊」だけを特定 ---
        # 中日スポーツの記事リストは通常 'item' クラスや 'news-list' 内にあります
        # かつ、リンク先が必ず '/chuspo/article/dragons/' で始まるものに限定します
        articles = soup.find_all('a', href=re.compile(r'^/chuspo/article/dragons/\d+'))

        new_entries = []
        seen_hrefs = set()

        for a_tag in articles:
            href = urllib.parse.urljoin(url, a_tag.get('href', ''))
            
            # メニュー類を除外するため、hrefに数字（記事ID）が含まれているかチェック
            if not re.search(r'\d{8,}', href): 
                continue
                
            if href in seen_hrefs: continue
            
            # 見出しを取得。中日スポーツは <span> や <h3> にタイトルが入ることが多い
            title = a_tag.get_text().strip()
            
            # 「もっと見る」や短すぎるメニュー名を排除（ニュース見出しは通常20文字以上）
            if len(title) < 18: continue 

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
            body {{ font-family: -apple-system, sans-serif; background: #f0f4f8; padding: 10px; margin: 0; }}
            .header {{ background:#0044cc; color:white; padding:15px; text-align:center; position: sticky; top: 0; z-index: 1000; border-bottom: 3px solid #ffcc00; }}
            .card {{ background: white; border-radius: 12px; padding: 18px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
            .summary-text {{ font-weight: bold; font-size: 1.1em; margin-bottom: 15px; line-height: 1.5; color: #1a1a1a; }}
            .btn-group {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
            .btn {{ text-align: center; text-decoration: none; padding: 12px; border-radius: 8px; font-weight: bold; }}
            .read-btn {{ background: #e7efff; color: #0044cc; }}
            .post-btn {{ background: #1d9bf0; color: white; }}
        </style>
    </head>
    <body>
        <div class="header"><h2 style="margin:0;">🐉 中スポ速報 ({now})</h2></div>
        <div style="margin-top:15px;">
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
        html_content += "<p style='text-align:center; padding:50px; color:#666;'>現在、新しいニュースはありません。</p>"
    html_content += "</div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    news = get_chuspo_news()
    create_html(news)
