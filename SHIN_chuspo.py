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

    # --- すべての日付パターンをあらかじめ作っておく ---
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.datetime.now(JST)
    yesterday = now - timedelta(days=1)

    # パターン1: 2026年4月22日 / 2026年4月21日 (漢字)
    today_kanji = now.strftime('%Y年%-m月%-d日')
    yesterday_kanji = yesterday.strftime('%Y年%-m月%-d日')

    # パターン2: 4/22 / 4/21 (スラッシュ)
    today_slash = now.strftime('%-m/%-d')
    yesterday_slash = yesterday.strftime('%-m/%-d')

    # すべてを「許可リスト」に入れる
    allowed_dates = [today_kanji, yesterday_kanji, today_slash, yesterday_slash, "時間前", "分前"]

    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = [line.strip() for line in f.readlines()]

    stock = []
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')

        # ニュースの塊（liやdiv）を探す
        items = soup.find_all(['li', 'div'], class_=re.compile(r'item|card|news-list'))
        
        new_entries = []
        seen_hrefs = set()

        for item in items:
            a_tag = item.find('a', href=True)
            if not a_tag: continue
            
            href = a_tag.get('href')
            if not re.search(r'/article/\d{7,}', href): continue
            full_url = urllib.parse.urljoin(url, href)
            if full_url in seen_hrefs: continue

            # --- 【判定】許可した日付パターンのどれかが含まれているか確認 ---
            item_text = item.get_text()
            if not any(date_str in item_text for date_str in allowed_dates):
                # どれにも当てはまらなければ、古い記事（4/12など）なので捨てる
                continue

            title = a_tag.get_text(strip=True)
            if len(title) < 18: continue 

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

# (create_html部分は変更なし)
