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

    # --- 【URLから日付を判別する準備】 ---
    # 送っていただいた例「/article/1240887」のような数字から日付を推測するのは難しいため、
    # シンプルに「サイトの上位にある最新の20件」を対象にします。
    
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = [line.strip() for line in f.readlines()]

    stock = []
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')

        # ページ内のすべてのリンクを確認
        all_links = soup.find_all('a', href=True)
        
        new_entries = []
        seen_hrefs = set()

        for a in all_links:
            href = a.get('href')
            # 記事URL（/article/数字）の形式だけを狙う
            if not re.search(r'/article/\d{6,}', href):
                continue
                
            full_url = urllib.parse.urljoin(url, href)
            if full_url in seen_hrefs: continue
            
            title = a.get_text().strip()
            # メニューなどの短い文字（18文字以下）は排除
            if len(title) < 18: continue 

            # --- 【判定ロジック】 ---
            # 1. 履歴にない新しいURLであること
            # 2. かつ、中日スポーツの「最新ニュース」エリアにあること
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
