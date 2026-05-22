import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# 第1試合（福岡vs神戸）のURL
url = "https://www.totoone.jp/match/27736"

print(f"🔄 {url} から実際に画面に描画されている全テキストを抽出します...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 1024},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    
    # ページを開いて通信が完全に終わるまで待機
    page.goto(url, wait_until="networkidle")
    
    # トラップ対策として、念のため物理的に3秒待機して完全に画面を切り替えさせます
    time.sleep(3.0)
    
    html_content = page.content()
    browser.close()

soup = BeautifulSoup(html_content, 'html.parser')

print("\n=============================================")
print("📋 【目視確認】画面内の全テキスト（上から順）")
print("=============================================")

# ページ内のすべての文字列を分解して、空行を除外して綺麗に並べる
lines = [line.strip() for line in soup.get_text().splitlines() if line.strip()]

print(f"総テキスト行数: {len(lines)}")
print("--- ここからログ開始 ---")

for idx, line in enumerate(lines):
    # ログが長すぎて途切れないよう、主要な部分（最初の200行）をしっかり出力
    print(f"[{idx:03d}] {line}")
    if idx >= 200:
        print("\n... (200行以降は省略) ...")
        break

print("--- ログ終了 ---")
