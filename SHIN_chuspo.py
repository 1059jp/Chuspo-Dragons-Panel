import requests
from bs4 import BeautifulSoup
import datetime
import os
import re
import urllib.parse
from datetime import timedelta, timezone

# --- 設定 ---
HISTORY_FILE = "CHUSPO_history.txt"

def build_summary(title):
    text = re.sub(r'\(.*?\)|（.*?）|【.*?】', '', title).strip()
    return f"{text}\n\n#dragons #中日スポーツ"

def get_chuspo_news():
    url = "https://www.chunichi.co.jp/chuspo/dragons"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 日付の準備（2026年4月22日、21日）
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.datetime.now(JST)
    t_str = now.strftime('%Y年%-m月%-d日')
    y_str = (now - timedelta(days=1)).strftime('%Y年%-m月%-d日')

    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = [line.strip() for line in f.readlines()]

    stock = []
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. ページ内のすべての「記事カード（liやdiv）」を特定
        # 中日スポーツのリスト構造を網羅的に探します
        items = soup.select('li, div[class*="item"], div[class*="card"]')
        
        new_entries = []
        seen_hrefs = set()

        for item in items:
            a_tag = item.find('a', href=True)
            if not a_tag: continue
            
            href = a_tag.get('href')
            if not re.search(r'/article/\d{6,}', href): continue
            full_url = urllib.parse.urljoin(url, href)
            if full_url in seen_hrefs: continue

            # 2. 【修正ポイント】タグの奥底にあるテキストもすべて結合して取得
            title = a_tag.get_text(strip=True)
            
            # 3. 日付のチェック（検証結果に基づいた「2026年4月21日」等の文字を探す）
            date_text = item.get_text()
            if not (t_str in date_text or y_str in date_text):
                # 日付が見つからない場合は、念のため「新着」として扱う（超速報対策）
                if "前" not in date_text and ":" not in date_text:
                    continue

            # 4. 短すぎるゴミデータを排除（20文字以上）
            if len(title) < 20: continue 

            if title not in history and full_url not in history:
                summary_text = build_summary(title)
                stock.append({"summary": summary_text, "url": full_url})
                new_entries.extend([title, full_url])
                history.extend([title, full_url])
                seen_hrefs.add(full_url)

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
            body {{ font-family: sans-serif; background: #f0f4f8; padding: 10px; margin: 0; }}
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
        html_content += "<p style='text-align:center; padding:50px; color:#666;'>新着ニュースはありません。<br>（履歴をリセットして再試行してください）</p>"
    html_content += "</div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    news = get_chuspo_news()
    create_html(news)
