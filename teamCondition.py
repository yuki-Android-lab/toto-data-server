import json
import re
import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

print("3️⃣ [teamCondition.py] スコア（数字）基準で直近5試合のコンディションを計算します...")

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

def parse_team_table_lines(soup, is_home=True):
    """
    トトワンのHTMLから、HOME側(左セル)またはAWAY側(右セル)の戦績テキスト行を正確に分離して回収
    """
    lines = []
    # ページ内のすべてのテーブル行(tr)を走査
    for tr in soup.find_all('tr'):
        cells = tr.find_all('td')
        # 左右にセルが並んでいる成績テーブルを対象にする
        if len(cells) >= 2:
            idx = 0 if is_home else 1
            txt = cells[idx].get_text().strip()
            
            # スコアの数字パターン（例：1-1 や 0-2）が含まれている行だけをターゲットにする
            if re.search(r"\d+-\d+", txt) and "/" in txt:
                if txt not in lines:
                    lines.append(txt)
    return lines

def analyze_recent_5(lines, team_name, is_self_top5, match_list):
    """
    〇●△マークは無視し、スコアの数字だけで勝・分・敗を再判定して計算する関数
    """
    wins, draws, losses, tough_losses = 0, 0, 0, 0
    processed_count = 0
    
    # 抽出した行の上から5試合分だけをループ
    for txt in lines[:5]:
        score_match = re.search(r"(\d+)-(\d+)", txt)
        if not score_match:
            continue
            
        processed_count += 1
        my_score = int(score_match.group(1))   # 自チームの得点
        opp_score = int(score_match.group(2))  # 相手チームの得点
        
        # 💡 マークではなく「スコアの数字」だけで勝敗をガチ判定する
        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            draws += 1
        else:
            losses += 1
            
            # 【裏ロジック救済判定】
            # 自分自身が1〜5位のチームでなく、かつ「1点差負け」の場合のみチェック
            if not is_self_top5 and (opp_score - my_score) == 1:
                # スコアより前の部分に書かれている対戦相手のテキストを取得
                opp_part = txt.split(score_match.group(0))[0]
                if check_if_opponent_is_top5(opp_part, match_list):
                    tough_losses += 1

    # 万が一データが1試合も引っかからなかった場合の安全弁
    if processed_count == 0:
        return "普通", 0.0, "0勝0分0敗(スコアパース空振り)"

    # 1〜5の基本ルール判定
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
        
    # 裏ロジック救済の発動
    if status == "悪化" and not is_self_top5:
        if wins == 0 and tough_losses >= 3:
            status = "普通"
            print(f"   ✨ 救済発動 [{team_name}]: スコア上0勝ですが上位に1点差負けが{tough_losses}試合あるため『普通』に引き上げ")
        elif wins > 0 and tough_losses >= 2:
            status = "普通"
            print(f"   ✨ 救済発動 [{team_name}]: スコア上{wins}勝ですが上位に1点差負けが{tough_losses}試合あるため『普通』に引き上げ")

    # 係数マッピング
    coef = 0.0
    if status == "良好":
        coef = 0.2
    elif status == "悪化":
        coef = -0.5
        
    return status, coef, f"{wins}勝{draws}分{losses}敗(スコア基準 / 上位への1点差負け:{tough_losses}試合)"


# 3. スクレイピングメイン処理
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
            
            # 自分自身が1〜5位のチームかどうかのフラグ
            is_home_top5 = get_top5_status(match_data['homeTeam'], match_list)
            is_away_top5 = get_top5_status(match_data['awayTeam'], match_list)
            
            # 左カラム(HOME)と右カラム(AWAY)のテキスト行をそれぞれ独立して取得
            home_lines = parse_team_table_lines(soup, is_home=True)
            away_lines = parse_team_table_lines(soup, is_home=False)
            
            # スコアベースでの戦績分析を実行
            home_status, home_coef, home_detail = analyze_recent_5(home_lines, match_data['homeTeam'], is_home_top5, match_list)
            away_status, away_coef, away_detail = analyze_recent_5(away_lines, match_data['awayTeam'], is_away_top5, match_list)
            
        except Exception as e:
            print(f"   ⚠️ エラー(試合No.{match_no}): {e}")
            home_status, home_coef, home_detail = "普通", 0.0, "エラーにより判定不能"
            away_status, away_coef, away_detail = "普通", 0.0, "エラーにより判定不能"
        finally:
            context.close()
            
        # JSONデータに反映
        match_data["homeCondition"] = home_status
        match_data["homeConditionCoef"] = home_coef
        match_data["awayCondition"] = away_status
        match_data["awayConditionCoef"] = away_coef
        
        h_tag = " [★現在1~5位]" if is_home_top5 else ""
        a_tag = " [★現在1~5位]" if is_away_top5 else ""
        
        print(f"   🏠 HOME {match_data['homeTeam']}{h_tag}: {home_detail} -> 判定:{home_status} ({home_coef})")
        print(f"   🚀 AWAY {match_data['awayTeam']}{a_tag}: {away_detail} -> 判定:{away_status} ({away_coef})")
        print("-" * 50)
        
    browser.close()

# 4. 保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("💾 [teamCondition.py] スコア数字による勝敗判定に切り替え、data.json を最終保存しました！")
