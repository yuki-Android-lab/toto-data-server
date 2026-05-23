import time
import json
import re
import os
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

print("2️⃣ [test_scrape.py] 既存の data.json に怪我人情報を追記します...")

TOP_URL = "https://www.totoone.jp/"
match_ids = []

# 1. トップページから13試合分のIDを取得
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    try:
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        init_page = context.new_page()
        init_page.goto(TOP_URL, wait_until="networkidle")
        html_top = init_page.content()
        match_ids = [int(x) for x in re.findall(r"/match/(\d+)", html_top)]
        context.close()
    except Exception as e:
        print(f"⚠️ TOPページからのID抽出に失敗しました: {e}")
    browser.close()

# 万が一のフォールバック用
if not match_ids:
    match_ids = [27736, 27737, 27738, 27739, 27740, 27741, 27742, 27743, 27744, 27745, 27746, 27747, 27748]

# 2. teamRank.py が作った data.json を読み込む
if not os.path.exists('data.json'):
    print("❌ data.json が見つかりません！先に teamRank.py を実行してください。")
    exit(1)

with open('data.json', 'r', encoding='utf-8') as f:
    match_list = json.load(f)

# 3. 怪我人スクレイピングとマージ処理
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    for i, match_data in enumerate(match_list):
        match_no = match_data["matchNo"]
        m_id = match_ids[i]
        
        target_url = f"https://www.totoone.jp/match/{m_id}"
        print(f"✈️ 解析中 (試合No.{match_no}): {target_url}")
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        home_injuries = []
        away_injuries = []
        
        try:
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            time.sleep(2)
            html_content = page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            
            for div in soup.find_all('div'):
                status_text = div.get_text().strip()
                if status_text in ["出場微妙", "欠場濃厚", "出場停止"]:
                    parent_box = div.find_parent()
                    if parent_box:
                        tags = [t for t in parent_box.children if t.name is not None]
                        status_index = -1
                        for s_idx, t in enumerate(tags):
                            if t.get_text().strip() == status_text:
                                status_index = s_idx
                                break
                        
                        if status_index != -1:
                            # HOME側
                            for t in tags[:status_index]:
                                for li in t.find_all('li'):
                                    txt = li.get_text().strip()
                                    p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                                    if p_match:
                                        name = p_match.group(1).strip()
                                        if name and name != "なし" and name not in home_injuries:
                                            home_injuries.append(name)
                                            
                            # AWAY側
                            for t in tags[status_index+1:]:
                                for li in t.find_all('li'):
                                    txt = li.get_text().strip()
                                    p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                                    if p_match:
                                        name = p_match.group(1).strip()
                                        if name and name != "なし" and name not in away_injuries:
                                            away_injuries.append(name)
                                            
        except Exception as e:
            print(f"   ⚠️ エラー(試合No.{match_no}): {e}")
        finally:
            context.close()

        # 既存データへの上書きマージ
        home_injuries_str = " / ".join(home_injuries) if home_injuries else "なし"
        away_injuries_str = " / ".join(away_injuries) if away_injuries else "なし"
        
        match_data["homeInjuries"] = home_injuries_str
        match_data["awayInjuries"] = away_injuries_str
        match_data["homeInjuriesCount"] = len(home_injuries)
        match_data["awayInjuriesCount"] = len(away_injuries)
        
        # 【修正】ログ出力部分に選手名（_str）を表示するように戻しました
        print(f"   📊 確定 -> {match_data['homeTeam']} vs {match_data['awayTeam']}")
        print(f"   🚨 離脱 -> H:{len(home_injuries)}人 ({home_injuries_str}) / A:{len(away_injuries)}人 ({away_injuries_str})")
        
    browser.close()

# 最終保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("💾 [test_scrape.py] 正しい順序のまま怪我人情報を追記し、data.json を最終保存しました！")
