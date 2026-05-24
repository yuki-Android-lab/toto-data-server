import json
import re
import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

print("3️⃣ [teamCondition.py] 直近5試合のコンディションを計算します（上位チームは救済対象外）...")

# 1. 既存の data.json を読み込む
if not os.path.exists('data.json'):
    print("❌ data.json が見つかりません！先に前段のスクリプトを実行してください。")
    exit(1)

with open('data.json', 'r', encoding='utf-8') as f:
    match_list = json.load(f)

# 2. 現在の「真の1〜5位チーム」をデータから正しく抽出
top5_teams = set()
for m in match_list:
    # 文字列の可能性を考慮して判定
    if "homeRank" in m and m["homeRank"] is not None:
        try:
            if 1 <= int(m["homeRank"]) <= 5:
                top5_teams.add(m["homeTeam"])
        except ValueError:
            pass
    if "awayRank" in m and m["awayRank"] is not None:
        try:
            if 1 <= int(m["awayRank"]) <= 5:
                top5_teams.add(m["awayTeam"])
        except ValueError:
            pass

print(f"📊 現在の1〜5位チーム（自身がこれに該当する場合は救済措置なし）: {list(top5_teams)}")

# 固定の13試合IDリスト
match_ids = [27736, 27737, 27738, 27739, 27740, 27741, 27742, 27743, 27744, 27745, 27746, 27747, 27748]

def analyze_recent_5(lines, team_name):
    """
    直近5試合のテキストリストから判定と係数を算出する関数
    """
    wins, draws, losses, tough_losses = 0, 0, 0, 0
    valid_lines = []
    
    # 〇●△が含まれる有効な行だけを抽出
    for line in lines:
        txt = line.get_text().strip()
        if any(s in txt for s in ["〇", "●", "△"]):
            valid_lines.append(txt)
            
    # 直近5試合分だけを精査
    for txt in valid_lines[:5]:
        match_symbol = re.search(r"([〇●△])", txt)
        score_match = re.search(r"(\d+)-(\d+)", txt)
        
        if not match_symbol:
            continue
            
        symbol = match_symbol.group(1)
        if symbol == "〇":
            wins += 1
        elif symbol == "△":
            draws += 1
        elif symbol == "●":
            losses += 1
            
            # 【裏ロジック用カウント】
            # ただし、自分自身が1〜5位のチームである場合は、対戦相手判定（救済数カウント）は行わない（スキップ）
            if team_name in top5_teams:
                continue
                
            if score_match:
                my_score = int(score_match.group(1))
                opp_score = int(score_match.group(2))
                # 負け（●）の時は相手の点数が高い。差が1なら1点差負け
                if (opp_score - my_score) == 1:
                    # 対戦相手が現在の1〜5位チームに含まれているか
                    for top_team in top5_teams:
                        if top_team in txt:
                            tough_losses += 1
                            break

    # 1〜5の基本ルール判定（これは1〜5位チームであっても全員一律で適用）
    if wins >= 4:
        status = "良好"
    elif wins == 3:
        status = "良好" if draws >= 1 else "普通"
    elif wins == 2:
        status = "普通" if draws >= 1 else "悪化"
    elif wins == 1:
        status = "普通" if draws >= 2 else "悪化"
    else:
        status = "悪化"
        
    # 裏ロジック救済の発動（自分自身が1〜5位のチームは、tough_lossesが常に0なのでここは発動しません）
    if status == "悪化":
        if wins == 0 and tough_losses >= 3:
            status = "普通"
            print(f"   ✨ 救済発動 [{team_name}]: 0勝ですが上位に1点差負けが{tough_losses}試合あるため『普通』に引き上げ")
        elif wins > 0 and tough_losses >= 2:
            status = "普通"
            print(f"   ✨ 救済発動 [{team_name}]: {wins}勝ですが上位に1点差負けが{tough_losses}試合あるため『普通』に引き上げ")

    # 係数マッピング
    coef = 0.0
    if status == "良好":
        coef = 0.2
    elif status == "悪化":
        coef = -0.5
        
    return status, coef, f"{wins}勝{draws}分{losses}敗(上位への1点差負け:{tough_losses}試合)"


# 3. スクレイピング処理
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    for i, match_data in enumerate(match_list):
        match_no = match_data["matchNo"]
        m_id = match_ids[i]
        
        target_url = f"https://www.totoone.jp/match/{m_id}"
        print(f"✈️ コンディション解析中 (試合No.{match_no}): {target_url}")
        
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
            
            home_lines = []
            away_lines = []
            
            # トトワンの「今シーズンの成績」テーブル行をパース
            for tr in soup.find_all('tr'):
                cells = tr.find_all('td')
                if len(cells) >= 2:
                    h_text = cells[0].get_text().strip()
                    a_text = cells[1].get_text().strip()
                    
                    if any(x in h_text for x in ["〇", "●", "△"]) or "/" in h_text:
                        home_lines.append(cells[0])
                    if any(x in a_text for x in ["〇", "●", "△"]) or "/" in a_text:
                        away_lines.append(cells[1])
                        
            # 各チームの判定を実行
            home_status, home_coef, home_detail = analyze_recent_5(home_lines, match_data['homeTeam'])
            away_status, away_coef, away_detail = analyze_recent_5(away_lines, match_data['awayTeam'])
            
        except Exception as e:
            print(f"   ⚠️ エラー(試合No.{match_no}): {e}")
            home_status, home_coef, home_detail = "普通", 0.0, "エラーにより判定不能"
            away_status, away_coef, away_detail = "普通", 0.0, "エラーにより判定不能"
        finally:
            context.close()
            
        # データのマージ
        match_data["homeCondition"] = home_status
        match_data["homeConditionCoef"] = home_coef
        match_data["awayCondition"] = away_status
        match_data["awayConditionCoef"] = away_coef
        
        print(f"   🏠 HOME {match_data['homeTeam']}: {home_detail} -> 判定:{home_status} ({home_coef})")
        print(f"   🚀 AWAY {match_data['awayTeam']}: {away_detail} -> 判定:{away_status} ({away_coef})")
        print("-" * 50)
        
    browser.close()

# 4. 保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("💾 [teamCondition.py] 正しい条件を反映し、data.json を最終保存しました！")
