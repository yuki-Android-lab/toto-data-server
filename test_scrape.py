import json
import re
import os
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

if not os.path.exists('data.json'):
    print("❌ data.json が見つかりません！先に fetch_toto.py を実行してください。")
    exit(1)

with open('data.json', 'r', encoding='utf-8') as f:
    match_list = json.load(f)

print("🔄 [test_scrape] 既存の data.json に離脱者情報を追記します...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    for match_data in match_list:
        match_no = match_data["matchNo"]
        base_match_id = match_data["holdId"]
        
        target_url = f"https://www.totoone.jp/match/{base_match_id + (match_no - 1)}"
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 離脱者テーブルはHTML内に初期から存在するため高速ロードでOK
            page.goto(target_url, wait_until="domcontentloaded")
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            home_injuries = []
            away_injuries = []
            
            # --- 離脱者情報の取得（実績のある安定ロジック） ---
            for div in soup.find_all('div'):
                status_text = div.get_text().strip()
                if status_text in ["出場微妙", "欠場濃厚", "出場停止"]:
                    parent_box = div.find_parent()
                    if parent_box:
                        tags = [t for t in parent_box.children if t.name is not None]
                        status_index = -1
                        for idx, t in enumerate(tags):
                            if t.get_text().strip() == status_text:
                                status_index = idx
                                break
                        
                        if status_index != -1:
                            # ホーム側
                            for t in tags[:status_index]:
                                for li in t.find_all('li'):
                                    txt = li.get_text().strip()
                                    p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                                    if p_match:
                                        name = p_match.group(1).strip()
                                        if name and name != "なし" and name not in home_injuries:
                                            home_injuries.append(name)
                                            
                            # アウェイ側
                            for t in tags[status_index+1:]:
                                for li in t.find_all('li'):
                                    txt = li.get_text().strip()
                                    p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                                    if p_match:
                                        name = p_match.group(1).strip()
                                        if name and name != "なし" and name not in away_injuries:
                                            away_injuries.append(name)

            home_injuries_str = " / ".join(home_injuries) if home_injuries else "なし"
            away_injuries_str = " / ".join(away_injuries) if away_injuries else "なし"
            
            # 既存の完璧なチーム名データを壊さずに、離脱者情報だけを上書き
            match_data["homeInjuries"] = home_injuries_str
            match_data["awayInjuries"] = away_injuries_str
            match_data["homeInjuriesCount"] = len(home_injuries)
            match_data["awayInjuriesCount"] = len(away_injuries)
            
            h_team = match_data.get("homeTeam")
            a_team = match_data.get("awayTeam")
            h_rank = match_data.get("homeRank")
            a_rank = match_data.get("awayRank")
            
            print(f"🌐 [試合No.{match_no}] {h_team}({h_rank}位) vs {a_team}({a_rank}位)")
            print(f"  👉 離脱追記: H {len(home_injuries)}人 ({home_injuries_str}) / A {len(away_injuries)}人 ({away_injuries_str})")

        except Exception as e:
            print(f"⚠️ 試合No.{match_no} 離脱者取得エラー（スキップします）: {e}")
            
        context.close()

    browser.close()

# 最終統合データを上書き保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("✨ 離脱者データの追記・統合がすべて正常に完了しました！")
