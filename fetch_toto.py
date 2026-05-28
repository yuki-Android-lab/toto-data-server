import time
import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

TOP_URL = "https://www.totoone.jp/"
match_list = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # 1. 最新の開催回の基準IDを自動抽出
    base_match_id = 27853 
    try:
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        init_page = context.new_page()
        init_page.goto(TOP_URL, wait_until="networkidle")
        html_top = init_page.content()
        match_ids = [int(x) for x in re.findall(r"/match/(\d+)", html_top)]
        if match_ids:
            base_match_id = min([idx for idx in match_ids if idx >= 27736])
        context.close()
    except:
        pass

    print(f"🔄 [fetch_toto] 基準ID: {base_match_id} から13試合の基本情報を取得します...")

    # 2. 13試合の解析
    for i in range(13):
        match_no = i + 1
        target_url = f"https://www.totoone.jp/match/{base_match_id + i}"
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 描画を確実に待つ
            page.goto(target_url, wait_until="networkidle")
            time.sleep(1.0)
            
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            home_team = f"ホーム{match_no}"
            away_team = f"アウェイ{match_no}"
            home_rank, away_rank = 10, 10
            
            # --- チーム名の取得（クラス名を見ず、タイトルタグ等から確実に分割） ---
            title_tag = soup.find('title')
            card_text = title_tag.get_text() if title_tag else ""
            
            if not card_text or not any(x in card_text.lower() for x in ["vs", "ｖｓ"]):
                # タイトルで取れなければ、OGPやh1から広く探す
                og_title = soup.find('meta', property='og:title')
                card_text = og_title.get('content') if og_title else soup.get_text()

            if card_text and any(x in card_text.lower() for x in ["vs", "ｖｓ"]):
                first_line = card_text.split("\n")[0].split("|")[0]
                parts = re.split(r'(?:VS|ｖｓ|vs)', first_line)
                if len(parts) >= 2:
                    h_cand = parts[0].strip().split()[-1] if parts[0].strip().split() else parts[0].strip()
                    a_cand = parts[1].strip().split()[0] if parts[1].strip().split() else parts[1].strip()
                    
                    # 順位テキストの除去
                    h_cand = re.sub(r'[\d\s]+位.*$', '', h_cand).strip()
                    a_cand = re.sub(r'[\d\s]+位.*$', '', a_cand).strip()
                    
                    if h_cand and a_cand and len(h_cand) < 10 and len(a_cand) < 10:
                        home_team = h_cand
                        away_team = a_cand

            # 順位の取得
            all_text = soup.get_text()
            rank_matches = re.findall(r"(\d+)\s*位", all_text)
            if len(rank_matches) >= 2:
                home_rank = int(rank_matches[0])
                away_rank = int(rank_matches[1])

            print(f"  ⚽ 試合No.{match_no}: {home_team}({home_rank}位) vs {away_team}({away_rank}位) 取得")

        except Exception as e:
            print(f"  ⚠️ 試合No.{match_no} 基本情報取得エラー: {e}")
            home_team, away_team = f"ホーム{match_no}", f"アウェイ{match_no}"
            home_rank, away_rank = 10, 10

        match_data = {
            "holdId": base_match_id,
            "matchNo": match_no,
            "homeTeam": home_team,
            "awayTeam": away_team,
            "homeRank": home_rank,
            "awayRank": away_rank,
            "homeGoalsFor": 15,
            "homeGoalsAgainst": 12,
            "homeWinRate": "40%",
            "awayGoalsFor": 18,
            "awayGoalsAgainst": 10,
            "awayWinRate": "55%",
            "homeRecent": "普通 [直近: ◯✕△◯✕]",
            "awayRecent": "好調 [直近: ◯◯△◯◯]" if away_rank < home_rank else "普通",
            "homeCompatibility": "普通",
            "homeTactics": "4-4-2",
            "awayCompatibility": "普通",
            "awayTactics": "4-2-3-1",
            "homeCondition": "普通",
            "homeInterval": "中6日",
            "awayCondition": "普通",
            "awayInterval": "中6日",
            "homeInjuries": "なし",
            "awayInjuries": "なし",
            "homeRainWinRate": "45%",
            "awayRainWinRate": "45%",
            "weather": "曇り",
            "homeInjuriesCount": 0,
            "awayInjuriesCount": 0
        }
        match_list.append(match_data)
        context.close()

    browser.close()

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)
print("✨ [fetch_toto] ベースの data.json を作成しました。")
