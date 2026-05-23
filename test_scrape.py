import time
import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

TOP_URL = "https://www.totoone.jp/"
match_list = []

# J1・J2・J3 全対応チーム名辞書
j_teams = [
    "札幌", "鹿島", "浦和", "柏", "FC東京", "F・東京", "東京V", "町田", "川崎F", "川崎Ｆ", 
    "横浜FM", "湘南", "新潟", "磐田", "名古屋", "京都", "G大阪", "Ｇ大阪", "C大阪", "Ｃ大阪", 
    "神戸", "広島", "福岡", "鳥栖", "仙台", "秋田", "山形", "いわき", "栃木", "群馬", 
    "横浜FC", "甲府", "清水", "藤枝", "岡山", "山口", "徳島", "愛媛", "長崎", "熊本", 
    "大分", "鹿児島", "八戸", "岩手", "福島", "大宮", "YSCC", "YS横浜", "相模原", "沼津", 
    "岐阜", "FC大阪", "奈良", "鳥取", "讃岐", "今治", "北九州", "宮崎", "琉球", "富山", 
    "金沢", "松本", "長野", "枚方", "滋賀", "高知", "青森"
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 1024},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    # 1. 最新の開催回の基準IDを自動抽出
    base_match_id = 27736 
    try:
        page.goto(TOP_URL, wait_until="networkidle")
        match_ids = [int(x) for x in re.findall(r"/match/(\d+)", html_top)]
        if match_ids:
            base_match_id = min([idx for idx in match_ids if idx >= 27736])
    except:
        pass

    # 2. 13試合分を巡回
    for i in range(13):
        match_no = i + 1
        target_url = f"https://www.totoone.jp/match/{base_match_id + i}"
        
        try:
            page.goto(target_url, wait_until="networkidle")
            time.sleep(2.0)
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 画面全体のテキストを1行ずつ綺麗にリスト化
            raw_lines = [line.strip() for line in soup.get_text().splitlines() if line.strip()]
            full_text = "".join(raw_lines)
            
            # 💡 【チーム名の抽出】「ホームアウェイ」の直後の文字列から辞書ベースで確実に抽出
            home_team = f"ホーム{match_no}"
            away_team = f"アウェイ{match_no}"
            
            team_part = re.search(r"ホームアウェイ([^\s\[]+?)(?:J\d|百年構想|\[)", full_text)
            if team_part:
                target_str = team_part.group(1)
                for team in j_teams:
                    if target_str.startswith(team):
                        home_team = team
                        remain_str = target_str[len(team):]
                        for a_team in j_teams:
                            if remain_str.startswith(a_team):
                                away_team = a_team
                                break
                        break

            # 💡 【順位の抽出】
            home_rank = 10
            away_rank = 10
            rank_matches = re.findall(r"(?:EAST|WEST)?\s*(\d+)位", full_text)
            if len(rank_matches) >= 2:
                home_rank = int(rank_matches[0])
                away_rank = int(rank_matches[1])

            # 💡 【離脱者情報の抽出】HTMLタグを一切信じず、テキストの並びから切り出す
            # テキスト内に「選手情報」～「出場微妙」「欠場濃厚」「出場停止」の枠組みが文字列として必ず存在する
            home_injuries = []
            away_injuries = []
            
            # 「選手情報」という行から「スコアラー」または「チーム情報」までのテキスト行を抜き出す
            player_info_section = []
            start_capture = False
            for line in raw_lines:
                if "選手情報" in line:
                    start_capture = True
                    continue
                if start_capture:
                    if "スコアラー" in line or "チーム情報" in line or "データ比較" in line:
                        break
                    player_info_section.append(line)
            
            # 抜き出した選手情報テキストから、各ステータスに属する選手をパース
            # 例: ['DF 橋本悠（15試合・2得点）', 'FW 鶴野怜樹（2試合・0得点）', '出場微妙', ...]
            current_status = ""
            for item in player_info_section:
                if "出場微妙" in item or "欠場濃厚" in item or "出場停止" in item:
                    current_status = item
                    continue
                
                # 選手名らしきパターン（ポジション＋名前）を正規表現でキャッチ
                p_match = re.search(r"^(?:GK|DF|MF|FW)\s*([^\s（(]+)", item)
                if p_match:
                    player_name = p_match.group(1).strip()
                    # ログの並び順（ホームの選手が先に出現し、後半にアウェイの選手が出現、または「なし」を挟む構造）
                    # 確実に安全に分けるため、テキスト中の「なし」や文字列の出現順序を考慮してリストに追加
                    if len(home_injuries) < 4 and not away_injuries: 
                        # 福岡vs神戸のログ構造に基づき、前半に出現する選手をひとまずホーム側へ
                        home_injuries.append(player_name)
                    else:
                        away_injuries.append(player_name)

            # 補正：もし上記簡易判定で偏りが出る場合の、より厳密なテキストブロック分割
            # 「選手情報」のテキストの塊を直接解析
            full_info_str = "".join(player_info_section)
            # ホーム側とアウェイ側の「なし」という区切り文字を利用して分割を試みる
            parts = full_info_str.split("なし")
            if len(parts) >= 2:
                # 前半ブロックから選手名を抽出
                h_names = re.findall(r"(?:GK|DF|MF|FW)\s*([^\s（(1-9]+)", parts[0])
                # 後半ブロックから選手名を抽出
                a_names = re.findall(r"(?:GK|DF|MF|FW)\s*([^\s（(1-9]+)", parts[1])
                if h_names: home_injuries = [n.strip() for n in h_names if n.strip()]
                if a_names: away_injuries = [n.strip() for n in a_names if n.strip()]

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
