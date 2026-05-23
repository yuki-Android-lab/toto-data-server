import time
import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

TOP_URL = "https://www.totoone.jp/"
match_list = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 1024},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    # 1. 基準IDの自動抽出
    base_match_id = 27736 
    try:
        page.goto(TOP_URL, wait_until="networkidle")
        html_top = page.content()
        match_ids = [int(x) for x in re.findall(r"/match/(\d+)", html_top)]
        if match_ids:
            base_match_id = min([idx for idx in match_ids if idx >= 27736])
    except:
        pass

    # 2. 13試合の解析
    for i in range(13):
        match_no = i + 1
        target_url = f"https://www.totoone.jp/match/{base_match_id + i}"
        
        try:
            page.goto(target_url, wait_until="domcontentloaded")
            
            # 💡 【超重要】画面が「完全にその試合のデータに切り替わる」のを物理的に監視
            # スクショにある黒ヘッダー「選手情報」の文字が画面に出現するまで、ブラウザを強制的に待機させます
            try:
                page.get_by_text("選手情報").wait_for(state="visible", timeout=8000)
            except:
                pass
            
            # 念のため、データが流し込まれるわずかなタイムラグとして1秒だけ追加固定待機
            time.sleep(1.0)
            
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # --- ① チーム名と順位の厳密取得 ---
            # 画面上部のメインヘッダー（Detail_matchCard__周辺）から現在の本物のカードを直接抜く
            home_team = f"ホーム{match_no}"
            away_team = f"アウェイ{match_no}"
            home_rank, away_rank = 10, 10
            
            # 対戦ヘッダーのテキストを回収
            card_area = soup.find(class_=lambda c: c and 'Detail_matchCard__' in c)
            if card_area:
                card_text = card_area.get_text()
                # チーム名らしき文字列を抽出（「福岡VS神戸」などの形を検知）
                teams = re.findall(r"([^\s\d位勝点]+?)\s*(?:VS|ｖｓ)\s*([^\s\d位勝点キックオフ]+)", card_text)
                if teams:
                    home_team, away_team = teams[0][0].strip(), teams[0][1].strip()
            
            # 順位部分（Detail_rank__）を個別ピンポイント取得
            rank_elements = soup.find_all(class_=lambda c: c and 'Detail_rank__' in c)
            if len(rank_elements) >= 2:
                h_r = re.search(r"\d+", rank_elements[0].get_text())
                a_r = re.search(r"\d+", rank_elements[1].get_text())
                if h_r: home_rank = int(h_r.group())
                if a_r: away_rank = int(a_r.group())

            # --- ② 離脱者（選手情報テーブル）の厳密パース ---
            home_injuries = []
            away_injuries = []
            
            # 「Detail_playerInfo__」クラスを持つ各ステータス行（出場微妙・欠場濃厚・出場停止）を完全ループ
            info_blocks = soup.find_all('div', class_=lambda c: c and 'Detail_playerInfo__' in c)
            
            for block in info_blocks:
                status_tag = block.find(class_=lambda c: c and 'Detail_memberInfo__' in c)
                if not status_tag:
                    continue
                status_text = status_tag.get_text().strip()
                
                # 離脱情報のみを対象とする
                if status_text in ["出場微妙", "欠場濃厚", "出場停止"]:
                    # 左側（ホーム）の解析
                    home_box = block.find(class_=lambda c: c and 'Detail_home__' in c)
                    if home_box:
                        for li in home_box.find_all('li'):
                            txt = li.get_text().strip()
                            p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                            if p_match:
                                name = p_match.group(1).strip()
                                if name and name != "なし" and name not in home_injuries:
                                    home_injuries.append(name)
                                    
                    # 右側（アウェイ）の解析
                    away_box = block.find(class_=lambda c: c and 'Detail_away__' in c)
                    if away_box:
                        for li in away_box.find_all('li'):
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
            home_team, away_team = f"ホーム{match_no}", f"アウェイ{match_no}"
            home_injuries_str, away_injuries_str = "なし", "なし"
            home_rank, away_rank, h_count, a_count = 10, 10, 0, 0

        # アプリ転送用JSONマッピング
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

    browser.close()

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)
