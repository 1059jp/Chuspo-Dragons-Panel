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
    text = re.sub(r'\(.*?\)|（.*?）|【.*?】', '', title).strip()
    return f"{text}\n\n#dragons #中日スポーツ"

def get_chuspo_news():
    url = "https://www.chunichi.co.jp/chuspo/dragons"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # --- 【検証結果に基づいた日付の準備】 ---
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.datetime.now(JST)
    
    # サイトの表記に合わせて「2026年4月22日」形式の文字列を作る
    today_str = now.strftime('%Y年%-m月%-d日')
    yesterday = now - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y年%-m月%-d日')

    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = [line.strip() for line in f.readlines()]

    stock = []
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')

        # ニュースの各項目を探す
        items = soup.find_all(['div', 'li', 'a'], class_=re.compile(r'item|card|news-list'))
        
        new_entries = []
        seen_hrefs = set()

        for item in items:
            # 1. 記事URLを特定
            a_tag = item if item.name == 'a' else item.find('a', href=True)
            if not a_tag: continue
            
            href = a_tag.get('href')
            if not re.search(r'/article/\d{6,}', href): continue
            full_url = urllib.parse.urljoin(url, href)
            if full_url in seen_hrefs: continue

            # 2. 【最重要】検証で判明した日付タグ(p class="sub-ttl"など)を探す
            # 一覧画面では別のクラス名(date, time等)の場合があるため柔軟に探します
            date_tag = item.find(['p', 'span'], class_=re.compile(r'sub-ttl|date|time'))
            date_text = date_tag.get_text() if date_tag else ""

            # 3. 日付チェック
            # 今日か昨日の文字列が含まれている、または日付が書いていない(＝超速報)場合のみ採用
            is_recent = (today_str in date_text) or (yesterday_str in date_text) or (not date_text)
            
            if not is_recent:
                continue

            # 4. タイトル取得と保存
            title = a_tag.get_text().strip()
            if len(title) < 20: continue

            if title not in history and full_url not in history:
                summary_text = build_summary(title)
                stock.insert(0, {"summary": summary_text, "url": full_url})
                new_entries.extend([title, full_url])
                history.extend([title, full_url])
                seen_hrefs.add(full_url)

        if new_entries:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                for entry in new_entries: f.write(entry + "\n")
                
    except Exception as e:
        print(f"Error: {e}")
    
    return stock[:20]
