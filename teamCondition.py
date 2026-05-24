import json
import re
import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

print("🔍 [DEBUGモード] 試合No.1のデータ構造を徹底的に調査します...")

# 1試合目のURL（福岡vs神戸）だけでテスト
target_url = "https://www.totoone.jp/match/27736"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 1024},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    
    try:
        page.goto(target_url, wait_until="networkidle", timeout=60000)
        time.sleep(3) # 読み込み安全マージン
        html_content = page.content()
        soup = BeautifulSoup(html_content, "html.parser")
        
        print("\n=== 🛠️ デバッグ1: ページ内の全テーブル行（tr）を走査します ===")
        all_trs = soup.find_all('tr')
        print(f"ページ内に見つかった <tr> タグの総数: {len(all_trs)}")
        
        count = 0
        for i, tr in enumerate(all_trs):
            cells = tr.find_all('td')
            tr_text = tr.get_text().strip().replace('\n', ' ')
            
            # ログが爆発するのを防ぐため、少しでも成績データっぽさがある行（/ や 〇 ● △ 数字）を抽出
            if any(k in tr_text for k in ["/", "〇", "●", "△", "-", "第"]):
                count += 1
                if count <= 40: # 最初の40行を表示
                    print(f"[行 {i}] セル数:{len(cells)} | 内容: {tr_text[:120]}")
                    
        print("\n=== 🛠️ デバッグ2: テーブル関係なく、スコア（数字-数字）を含む要素を直撃スキャン ===")
        score_elements = soup.find_all(lambda tag: tag.name in ['td', 'div', 'li'] and re.search(r"\d+-\d+", tag.get_text()))
        print(f"スコアらしき文字を含む要素の総数: {len(score_elements)}")
        for j, elem in enumerate(score_elements[:15]):
            print(f"[要素 {j}] タグ名:{elem.name} | 内容: {elem.get_text().strip().replace('\n', ' ')[:100]}")

    except Exception as e:
        print(f"❌ デバッグ中にエラー発生: {e}")
    finally:
        context.close()
        browser.close()

print("\n🔍 DEBUG終了。上記の出力結果を教えてください。")
