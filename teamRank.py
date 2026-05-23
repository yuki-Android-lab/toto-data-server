import json
import re
import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

if not os.path.exists('data.json'):
    print("❌ data.json が見つかりません！先に fetch_toto.py を実行してください。")
    exit(1)

with open('data.json', 'r', encoding='utf-8') as f:
    match_list = json.load(f)

print("🔄 [teamRank] 既存の data.json にNext.js生データから離脱者情報を追記します...")

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
            # ページアクセス（ネットワークが落ち着くまで待機）
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            time.sleep(2)
            
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            home_injuries = []
            away_injuries = []
            
            # --- 💡核心部：Next.jsの生JSONデータを直接ハッキングする ---
            next_data_script = soup.find('script', id='__NEXT_DATA__')
            
            if next_data_script and next_data_script.string:
                raw_json_text = next_data_script.string
                
                # JSONテキスト全体から「ポジション 選手名 ステータス」の並びを正規表現で一括抽出
                # 例: "DF 選手名 欠場濃厚", "FW 選手名 出場停止" などのパターンを網羅
                pattern = r'(GK|DF|MF|FW)\s+([^\s"\'）\)]+)\s+([^\s"\'\\]*(?:欠場|出場停止|出場微妙|離脱)[^\s"\'\\]*)'
                matches = re.findall(pattern, raw_json_text)
                
                # 抽出したデータを前半（ホーム）と後半（アウェイ）に安全に振り分ける
                # Next.jsのデータ構造上、ホームの選手データが先に出現し、その後アウェイの選手が出現します
                half_point = len(matches) // 2
                
                for i, match in enumerate(matches):
                    pos, name, status = match
                    name = name.strip()
                    # 特殊文字や不要なゴミの除去
                    name = re.sub(r'\\u[0-9a-fA-F]{4}', '', name) 
                    
                    if name and name != "なし":
                        if i < half_point:
                            if name not in home_injuries:
                                home_injuries.append(name)
                        else:
                            if name not in away_injuries:
                                away_injuries.append(name)
            
            # バックアップ：もし上記で見つからない場合、文字列全体から力技で抽出
            if not home_injuries and not away_injuries:
                # HTML全体のテキストからダイレクトに検索
                all_text = soup.get_text()
                backup_matches = re.findall(r'(GK|DF|MF|FW)\s+([^\s（\(\n]+)\s*(?:欠場|出場停止|出場微妙)', all_text)
                for pos, name in backup_matches:
                    name = name.strip()
                    if name and name != "なし" and name not in home_injuries:
                        home_injuries.append(name)

            home_injuries_str = " / ".join(home_injuries) if home_injuries else "なし"
            away_injuries_str = " / ".join(away_injuries) if away_injuries else "なし"
            
            # 既存のデータを壊さずに、離脱者情報だけを上書き
            match_data["homeInjuries"] = home_injuries_str
            match_data["awayInjuries"] = away_injuries_str
            match_data["homeInjuriesCount"] = len(home_injuries)
            match_data["awayInjuriesCount"] = len(away_injuries)
            
            h_team = match_data.get("homeTeam")
            a_team = match_data.get("awayTeam")
            h_rank = match_data.get("homeRank")
            a_rank = match_data.get("awayRank")
            
            print(f"🌐 [試合No.{match_no}] {h_team}({h_rank}位) vs {a_team}({a_rank}位)")
            print(f"   👉 離脱追記: H {len(home_injuries)}人 ({home_injuries_str}) / A {len(away_injuries)}人 ({away_injuries_str})")

        except Exception as e:
            print(f"⚠️ 試合No.{match_no} 離脱者取得エラー（スキップします）: {e}")
            
        context.close()
