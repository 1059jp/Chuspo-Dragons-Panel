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
OWNER = "1059jp"
REPO = "Chuspo-Dragons-Panel"
WORKFLOW_FILE = "main.yml" 

def build_summary(title):
    text = re.sub(r'\(.*?\)|（.*?）|【.*?】', '', title).strip()
    return f"{text}\n\n#dragons #中日ドラゴンズ"

def get_chuspo_news():
    url = "https://www.chunichi.co.jp/chuspo/dragons"
    headers = {"User-Agent": "Mozilla/5.0"}
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = [line.strip() for line in f.readlines()]
    stock = []
    if os.path.exists(STOCK_FILE):
        try:
            with open(STOCK_FILE, "r", encoding="utf-8") as f:
                stock = json.load(f)
        except: stock = []

    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        all_links = soup.find_all('a', href=True)
        new_entries = []
        for a in all_links:
            href = a.get('href')
            if not re.search(r'/article/\d{6,}', href): continue
            full_url = urllib.parse.urljoin(url, href)
            title = a.get_text().strip()
            if len(title) < 20 or title in history or full_url in history: continue
            
            summary_text = build_summary(title)
            stock.insert(0, {"summary": summary_text, "url": full_url})
            new_entries.extend([title, full_url])
            history.extend([title, full_url])

        if new_entries:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                for entry in new_entries: f.write(entry + "\n")
        
        stock = stock[:30]
        with open(STOCK_FILE, "w", encoding="utf-8") as f:
            json.dump(stock, f, ensure_ascii=False, indent=4)
    except Exception as e: print(f"Error: {e}")
    return stock

def create_html(news_list):
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.datetime.now(JST).strftime('%m/%d %H:%M')
    
    # 【最重要】鍵を一切書き込まないJSコード
    js_code = """
    function removeCard(btn) { btn.closest('.card').remove(); }
    function reloadPage() { location.reload(); }

    async function triggerSystemUpdate() {
        // ブラウザの保存領域から鍵を取り出す（最初は空っぽ）
        let token = localStorage.getItem('GH_TOKEN');
        
        if(!token) {
            token = prompt("【初回のみ】GitHubのトークンを入力してください。\\n(ブラウザに安全に保存され、コードには書き込まれません)");
            if(token) localStorage.setItem('GH_TOKEN', token);
        }
        if(!token) return;

        const btn = document.querySelector('.system-btn');
        btn.innerText = "⏳ 実行中...";
        btn.disabled = true;

        try {
            const response = await fetch('https://api.github.com/repos/""" + OWNER + "/" + REPO + """/actions/workflows/""" + WORKFLOW_FILE + """/dispatches', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Accept': 'application/vnd.github.v3+json'
                },
                body: JSON.stringify({ ref: 'main' })
            });

            if (response.status === 204) {
                alert("システムを起動しました！\\n約1分後に更新ボタンを押してください。");
            } else if(response.status === 401) {
                alert("鍵が無効です。入力をやり直してください。");
                localStorage.removeItem('GH_TOKEN');
            } else {
                alert("エラーが発生しました。");
            }
        } catch (e) {
            alert("通信失敗。ネット接続を確認してください。");
        } finally {
            btn.innerText = "🚀 システム更新";
            btn.disabled = false;
        }
    }
    """
    
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
            .refresh-btn {{ background: #ffcc00; color: #0044cc; border: none; padding: 8px 12px; border-radius: 20px; font-weight: bold; cursor: pointer; }}
            .system-btn {{ background: #ff4444; color: white; border: none; padding: 8px 12px; border-radius: 20px; font-weight: bold; cursor: pointer; }}
            .card {{ background: white; border-radius: 12px; padding: 18px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); position: relative; }}
            .close-btn {{ position: absolute; top: 10px; right: 10px; color: #ccc; font-size: 24px; cursor: pointer; border: none; background: none; }}
            .summary-text {{ font-weight: bold; font-size: 1.1em; margin-bottom: 15px; color: #1a1a1a; }}
            .btn-group {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
            .btn {{ text-align: center; text-decoration: none; padding: 12px; border-radius: 8px; font-weight: bold; }}
            .read-btn {{ background: #e7efff; color: #0044cc; }}
            .post-btn {{ background: #1d9bf0; color: white; }}
        </style>
        <script>{js_code}</script>
    </head>
    <body>
        <div class="header">
            <div style="font-weight:bold;">🐉 ({now})</div>
            <div>
                <button onclick="triggerSystemUpdate()" class="system-btn">🚀 システム更新</button>
                <button onclick="reloadPage()" class="refresh-btn">🔄 更新</button>
            </div>
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
    if not news_list: html_content += "<p style='text-align:center;'>新着なし</p>"
    html_content += "</div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(html_content)

if __name__ == "__main__":
    news = get_chuspo_news()
    create_html(news)
