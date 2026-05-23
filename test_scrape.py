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
    base_match_id = 27736 
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

    # 2. 13試合の解析
    for i in range(13):
        match_no = i + 1
        target_url = f"https://www.totoone.jp/match/{base_match_id + i}"
        
        # 1試合ごとに完全にクリーンなタブを開く
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(target_url, wait_until="networkidle")
            time.sleep(2.5)  # レンダリングの完全な安全マージン
            
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # --- ① チーム名と順位の取得（セレクターをクラス名部分一致に修正） ---
            home_team = f"ホーム{match_no}"
            away_team = f"アウェイ{match_no}"
            home_rank, away_rank = 10, 10
            
            # 対戦カードヘッダーのテキストをクラス部分一致で取得
            card_area = soup.select_one('div[class*="Detail_matchCard__"]')
            if card_area:
                card_text = card_area.get_text()
                teams = re.findall(r"([^\s\d位勝点]+?)\s*(?:VS|ｖｓ)\s*([^\s\d位勝点キックオフ]+)", card_text)
                if teams:
                    home_team, away_team = teams[0][0].strip(), teams[0][1].strip()
            
            # 順位をクラス部分一致でピンポイント取得
            rank_elements = soup.select('p[class*="Detail_rank__"]')
            if len(rank_elements) >= 2:
                h_r = re.search(r"\d+", rank_elements[0].get_text())
                a_r = re.search(r"\d+", rank_elements[1].get_text())
                if h_r: home_rank = int(h_r.group())
                if a_r: away_rank = int(a_r.group())

            # --- ② 離脱者情報の取得（テーブル構造のCSSセレクターを厳密化） ---
            home_injuries = []
            away_injuries = []
            
            # 「Detail_playerInfo__」を含む各行を正確にループ
            info_blocks = soup.select('div[class*="Detail_playerInfo__"]')
            
            for block in info_blocks:
                # 状態（出場微妙、欠場濃厚、出場停止）のラベルをチェック
                status_tag = block.select_one('[class*="Detail_memberInfo__"]')
                if not status_tag:
                    continue
                status_text = status_tag.get_text().strip()
                
                if status_text in ["出場微妙", "欠場濃厚", "出場停止"]:
                    # 左側（ホーム）の離脱選手
                    home_box = block.select_one('[class*="Detail_home__"]')
                    if home_box:
                        for li in home_box.select('li'):
                            txt = li.get_text().strip()
                            # 「ポジション 選手名」の形から名前のみを切り出す
                            p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                            if p_match:
                                name = p_match.group(1).strip()
                                if name and name != "なし" and name not in home_injuries:
                                    home_injuries.append(name)
                                    
                    # 右側（アウェイ）の離脱選手
                    away_box = block.select_one('[class*="Detail_away__"]')
                    if away_box:
                        for li in away_box.select('li'):
                            txt = li.get_text().strip()
                            p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                            if p_match:
                                name = p_match.group(1).strip()
                                if name and name != "なし" and name not in away_injuries:
                                    away_injuries.append(name)

            home_injuries_str = " / ".join(home_injuries) if home_injuries else "なし"
            away_injuries_str = " / ".join(away_injuries) if away_injuries else "なし"
            h_count = len(home_injuries)
            a_count = len(away_injuries)

            print(f"🌐 [試合No.{match_no}] {home_team}({home_rank}位) vs {away_team}({away_rank}位)")
            print(f"  👉 離脱: H {h_count}人 ({home_injuries_str}) / A {a_count}人 ({away_injuries_str})")

        except Exception as e:
            # 万が一エラーが起きた場合は即時ログを吐き出す
            print(f"⚠️ 試合No.{match_no} 解析エラー: {e}")
            home_team, away_team = f"ホーム{match_no}", f"アウェイ{match_no}"
            home_injuries_str, away_injuries_str = "なし", "なし"
            home_rank, away_rank, h_count, a_count = 10, 10, 0, 0

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
            "homeInjuries": home_injuries_str,
            "awayInjuries": away_injuries_str,
            "homeRainWinRate": "45%",
            "awayRainWinRate": "45%",
            "weather": "曇り",
            "homeInjuriesCount": h_count,
            "awayInjuriesCount": a_count
        }
        match_list.append(match_data)
        context.close()

    browser.close()

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)
