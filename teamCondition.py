import json
import re
import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

print("3️⃣ [teamCondition.py] 解析用テキストの抽出とデバッグ出力を実行します...")

# 1. 既存の data.json を読み込む
if not os.path.exists('data.json'):
    print("❌ data.json が見つかりません！先に前段のスクリプトを実行してください。")
    exit(1)

with open('data.json', 'r', encoding='utf-8') as f:
    match_list = json.load(f)

# 固定の13試合IDリスト
match_ids = [27736, 27737, 27738, 27739, 27740, 27741, 27742, 27743, 27744, 27745, 27746, 27747, 27748]

def get_top5_status(team_name, match_list):
    """対象チームが現在1〜5位の上位チームであるかを厳密に判定"""
    for m in match_list:
        if m["homeTeam"] == team_name and "homeRank" in m and m["homeRank"] is not None:
            if 1 <= int(m["homeRank"]) <= 5: return True
        if m["awayTeam"] == team_name and "awayRank" in m and m["awayRank"] is not None:
            if 1 <= int(m["awayRank"]) <= 5: return True
    return False

def check_if_opponent_is_top5(opp_name, match_list):
    """対戦相手のチーム名が現在1〜5位かを判定"""
    for m in match_list:
        if m["homeTeam"] in opp_name and "homeRank" in m and m["homeRank"] is not None:
            if 1 <= int(m["homeRank"]) <= 5: return True
        if m["awayTeam"] in opp_name and "awayRank" in m and m["awayRank"] is not None:
            if 1 <= int(m["awayRank"]) <= 5: return True
    return False

def analyze_recent_4(text_list, team_name, is_self_top5, match_list):
    """
    【4試合割り切り】スコアから勝・分・敗を判定してトレンドを出す
    """
    wins, draws, losses, tough_losses = 0, 0, 0, 0
    processed_count = 0
    
    for txt in text_list:
        if processed_count >= 4:
            break
            
        score_match = re.search(r"(\d+)-(\d+)", txt)
        if not score_match:
            continue
            
        processed_count += 1
        my_score = int(score_match.group(1))
        opp_score = int(score_match.group(2))
        
        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            draws += 1
        else:
            losses += 1
            
            # 【裏ロジック救済判定】
            if not is_self_top5 and (opp_score - my_score) == 1:
                opp_part = txt.split(score_match.group(0))[0]
                if check_if_opponent_is_top5(opp_part, match_list):
                    tough_losses += 1

    if processed_count == 0:
        return "普通", 0.0, "0勝0分0敗(データなし)"

    if wins >= 3:
        status = "良好"
    elif wins == 2 and draws == 2:
        status = "良好"
    elif wins == 2 or (wins == 1 and draws >= 1):
        status = "普通"
    else:
        status = "悪化"
        
    if status == "悪化" and not is_self_top5:
        if tough_losses >= 2:
            status = "普通"

    coef = 0.0
    if status == "良好":
        coef = 0.2
    elif status == "悪化":
        coef = -0.5
        
    return status, coef, f"{wins}勝{draws}分{losses}敗(直近{processed_count}試合ベース)"


# Jリーグのチーム名リスト
ALL_TEAMS = [
    "札幌", "仙台", "秋田", "山形", "いわき", "鹿島", "水戸", "栃木", "群馬", "浦和", 
    "大宮", "千葉", "柏", "FC東京", "東京V", "町田", "川崎F", "横浜FM", "横浜FC", "湘南", 
    "甲府", "松本", "新潟", "富山", "金沢", "清水", "藤枝", "磐田", "名古屋", "岐阜", 
    "京都", "G大阪", "C大阪", "神戸", "奈良", "鳥取", "岡山", "広島", "山口", 
    "讃岐", "徳島", "愛媛", "今治", "福岡", "北九州", "鳥栖", "長崎", "熊本", "大分", "宮崎", "鹿児島", "琉球"
]

# 3. スクレイピングメイン処理
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # ログが長大になるのを防ぐため、まずは直近でおかしかった「試合No.1〜3」に絞ってデバッグします
    for i in range(3):
        match_data = match_list[i]
        match_no = match_data["matchNo"]
        m_id = match_ids[i]
        
        home_team = match_data['homeTeam']
        away_team = match_data['awayTeam']
        
        target_url = f"https://www.totoone.jp/match/{m_id}"
        print(f"\n==================================================")
        print(f"📊 【デバッグ】試合No.{match_no}: {home_team} vs {away_team}")
        print(f"==================================================")
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            time.sleep(2)
            html_content = page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            
            is_home_top5 = get_top5_status(home_team, match_list)
            is_away_top5 = get_top5_status(away_team, match_list)
            
            # 💡 【デバッグ確認用】抽出条件に引っかかるテキストをすべて一旦フラットに並べる
            all_scraped_texts = []
            for tag in soup.find_all(['li', 'td', 'div', 'p']):
                txt = tag.get_text().strip().replace('\n', ' ')
                if "/" in txt and re.search(r"\d+-\d+", txt):
                    if txt not in all_scraped_texts and len(txt) < 120:
                        all_scraped_texts.append(txt)
            
            # 🔍 スクレイピングで拾えた生のデータを最優先で全部出力する
            print(f"🗂️ [生データログ] ページ内から抽出された戦績テキスト（計 {len(all_scraped_texts)} 件）:")
            for idx, raw_txt in enumerate(all_scraped_texts):
                print(f"   [{idx}] {raw_txt}")
            
            # 仕分け処理（前回のロジックのまま、ログ出力のために一旦通します）
            home_texts = []
            away_texts = []
            for t in all_scraped_texts:
                opp_team = None
                for team in ALL_TEAMS:
                    if team in t:
                        opp_team = team
                        break
                if not opp_team:
                    continue
                
                if home_team in t and away_team not in t:
                    away_texts.append(t)
                elif away_team in t and home_team not in t:
                    home_texts.append(t)
                else:
                    if len(home_texts) < 6:
                        home_texts.append(t)
                    else:
                        away_texts.append(t)

            # 🔍 仕分けられた後の最終的な中身もログに出す
            print(f"\n   🏠 HOME [{home_team}] に振り分けられたテキスト:")
            for ht in home_texts[:4]: print(f"      -> {ht}")
            print(f"   🚀 AWAY [{away_team}] に振り分けられたテキスト:")
            for at in away_texts[:4]: print(f"      -> {at}")
            
            home_status, home_coef, home_detail = analyze_recent_4(home_texts, home_team, is_home_top5, match_list)
            away_status, away_coef, away_detail = analyze_recent_4(away_texts, away_team, is_away_top5, match_list)
            
            print(f"\n   結果 -> HOME: {home_detail} | AWAY: {away_detail}")
            
        except Exception as e:
            print(f"   ⚠️ エラー: {e}")
        finally:
            context.close()
        print("-" * 50)
        
    browser.close()
