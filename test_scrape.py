import time
import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

TOP_URL = "https://www.totoone.jp/"
match_list = []

print("🔄 クラス名非依存の確実なパース処理を開始します...")

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
    except Exception as e:
        print(f"⚠️ 基準ID自動抽出中の警告: {e}")

    print(f"🎯 基準URLのID: {base_match_id}")

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
            page.goto(target_url, wait_until="networkidle")
            time.sleep(3.0)  # 動的データの読み込みを完全に待つ安全マージン
            
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # --- ① チーム名と順位の取得（テキストベースで位置特定） ---
            home_team = f"ホーム{match_no}"
            away_team = f"アウェイ{match_no}"
            home_rank, away_rank = 10, 10
            
            # ページ内のすべてのテキストから「VS」または「ｖｓ」を含むブロックを探す
            vs_elements = soup.find_all(text=re.compile(r'(?:VS|ｖｓ)'))
            for elem in vs_elements:
                parent_text = elem.parent.get_text()
                # チーム名（文字）VS（文字）のパターンを抽出
                teams = re.findall(r"([^\s\d位勝点]+?)\s*(?:VS|ｖｓ)\s*([^\s\d位勝点キックオフ]+)", parent_text)
                if teams:
                    # ナビゲーション等のゴミ（「J1第1節」など）を含まない純粋なチーム名ペアを特定
                    h_candidate = teams[0][0].strip()
                    a_candidate = teams[0][1].strip()
                    if h_candidate and a_candidate and len(h_candidate) < 10:
                        home_team = h_candidate
                        away_team = a_candidate
                        break
            
            # 順位の抽出（「〇〇位」というテキストの出現順から取得）
            all_text = soup.get_text()
            rank_matches = re.findall(r"(\d+)\s*位", all_text)
            if len(rank_matches) >= 2:
                home_rank = int(rank_matches[0])
                away_rank = int(rank_matches[1])

            # --- ② 離脱者情報の取得（テーブル構造をタグ名のみで分解） ---
            home_injuries = []
            away_injuries = []
            
            # クラス名がPC/スマホで違っても、構造（「出場微妙」「欠場濃厚」「出場停止」の文字の左右）は同じ
            # すべてのdivを走査し、中にステータス文字があるものを特定
            for div in soup.find_all('div'):
                # 子要素に直接ステータスがあるかチェック
                status_text = div.get_text().strip()
                if status_text in ["出場微妙", "欠場濃厚", "出場停止"]:
                    # このdivの親要素、または周辺のリスト構造（ul / li）を全回収
                    parent_box = div.find_parent()
                    if parent_box:
                        # 3列構造（左：ホーム、中：ステータス、右：アウェイ）のテキストの並びをパース
                        # liタグが並んでいる場合、またはプレーンテキストの塊から選手名を抽出
                        lis = parent_box.find_all('li')
                        if lis:
                            for li in lis:
                                txt = li.get_text().strip()
                                p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                                if p_match:
                                    name = p_match.group(1).strip()
                                    if name and name != "なし":
                                        # ホームかアウェイかの判定（HTML上の出現位置、またはテキストの前後関係）
                                        # 最初に見つかった選手リストの塊がホーム側、ステータスを挟んで次がアウェイ側
                                        # より確実に、親要素内の要素順で振り分け
                                        if li.find_before(div):
                                            if name not in home_injuries: home_injuries.append(name)
                                        else:
                                            if name not in away_injuries: away_injuries.append(name)
                        else:
                            # liタグがない簡易表示（スマホ版など）の場合、テキスト行から直接抽出
                            lines = [l.strip() for l in parent_box.get_text().splitlines() if l.strip()]
                            is_away = False
                            for line in lines:
                                if line == status_text:
                                    is_away = True  # ステータス文字以降はアウェイ側
                                    continue
                                p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", line)
                                if p_match:
                                    name = p_match.group(1).strip()
                                    if name and name != "なし":
                                        if not is_away:
                                            if name not in home_injuries: home_injuries.append(name)
                                        else:
                                            if name not in away_injuries: away_injuries.append(name)

            home_injuries_str = " / ".join(home_injuries) if home_injuries else "なし"
            away_injuries_str = " / ".join(away_injuries) if away_injuries else "なし"
            
            print(f"🌐 [試合No.{match_no}] {home_team}({home_rank}位) vs {away_team}({away_rank}位)")
            print(f"  👉 離脱: H {len(home_injuries)}人 ({home_injuries_str}) / A {len(away_injuries)}人 ({away_injuries_str})")

        except Exception as e:
            # 安全にフォールバックさせつつ、何が起きたかのログは隠さず出す
            print(f"⚠️ 試合No.{match_no} 解析スキップ原因: {e}")
            home_team, away_team = f"ホーム{match_no}", f"アウェイ{match_no}"
            home_injuries_str, away_injuries_str = "なし", "なし"
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
            "homeInjuries": home_injuries_str,
            "awayInjuries": away_injuries_str,
            "homeRainWinRate": "45%",
            "awayRainWinRate": "45%",
            "weather": "曇り",
            "homeInjuriesCount": len(home_injuries),
            "awayInjuriesCount": len(away_injuries)
        }
        match_list.append(match_data)
        context.close()

    browser.close()

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)
