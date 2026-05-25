import json
import re
import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

print("3️⃣ [teamCondition.py] 生データ構造のデバッグ出力＆勝敗判定ロジックを実行します...")

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

def analyze_recent_4(text_list, team_name, is_self_top5, match_list, role_label):
    """
    【検証用デバッグ機能付き】(H)/(A)を識別し、各試合のパース結果をログに出しながらトレンドを計算
    """
    wins, draws, losses, tough_losses = 0, 0, 0, 0
    processed_count = 0
    
    print(f"\n     --- 【{role_label}勝敗判定の内訳ログ: {team_name}】 ---")
    
    for txt in text_list:
        if processed_count >= 4:
            break
            
        score_match = re.search(r"(\d+)-(\d+)", txt)
        if not score_match:
            print(f"      [スキップ] スコア未検出: {txt}")
            continue
            
        processed_count += 1
        val_left = int(score_match.group(1))
        val_right = int(score_match.group(2))
        
        # (H)か(A)かで自チームの得点を識別
        if "（A）" in txt or "(A)" in txt:
            is_home_game = False
            my_score = val_right
            opp_score = val_left
            loc_label = "アウェイ(A)"
        else:
            is_home_game = True
            my_score = val_left
            opp_score = val_right
            loc_label = "ホーム(H)"
            
        # 勝敗の決定
        if my_score > opp_score:
            result_str = "○ 勝ち"
            wins += 1
        elif my_score == opp_score:
            result_str = "△ 引き分け"
            draws += 1
        else:
            result_str = "● 負け"
            losses += 1
            # 裏ロジック救済判定
            if not is_self_top5 and (opp_score - my_score) == 1:
                opp_part = txt.split(score_match.group(0))[0]
                if check_if_opponent_is_top5(opp_part, match_list):
                    tough_losses += 1
                    result_str += "（★上位への1点差負け・救済対象）"

        # 1試合ずつのパース結果をコンソールに完全表示
        print(f"      [{processed_count}戦目] 元データ: {txt}")
        print(f"              解釈: {loc_label} / 自スコア:{my_score}点 vs 相手:{opp_score}点 -> 判定: {result_str}")

    if processed_count == 0:
        return "普通", 0.0, "0勝0分0敗(データなし)"

    # トレンド判定基準
    if wins >= 3:
        status = "良好"
    elif wins == 2 and draws == 2:
        status = "良好"
    elif wins == 2 or (wins == 1 and draws >= 1):
        status = "普通"
    else:
        status = "悪化"
        
    # 裏ロジック救済
    if status == "悪化" and not is_self_top5:
        if tough_losses >= 2:
            status = "普通"
            print(f"      ✨ 救済発動 [{team_name}]: 直近4戦で上位へ1点差負けが{tough_losses}試合あるため『普通』に引き上げ")

    coef = 0.0
    if status == "良好":
        coef = 0.2
    elif status == "悪化":
        coef = -0.5
        
    return status, coef, f"{wins}勝{draws}分{losses}敗(直近{processed_count}試合ベース / 救済カウント:{tough_losses})"


# 3. スクレイピングメイン処理
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    for i, match_data in enumerate(match_list):
        match_no = match_data["matchNo"]
        m_id = match_ids[i]
        
        home_team = match_data['homeTeam']
        away_team = match_data['awayTeam']
        
        target_url = f"https://www.totoone.jp/match/{m_id}"
        print(f"\n==================================================================================")
        print(f"📊 試合No.{match_no}: {home_team} vs {away_team}")
        print(f"🔗 URL: {target_url}")
        print(f"==================================================================================")
        
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
            
            # ページ内から戦績テキストを抽出（重複排除）
            all_scraped_texts = []
            for tag in soup.find_all(['li', 'td', 'div']):
                txt = tag.get_text().strip().replace('\n', ' ')
                if "/" in txt and re.search(r"\d+-\d+", txt):
                    if txt not in all_scraped_texts and len(txt) < 100:
                        all_scraped_texts.append(txt)
            
            # 🔍 【検証デバッグ】ページから引っこ抜いた全データをそのまま表示
            print(f"🗂️ [生データログ] ページ内から検出された戦績テキスト（計 {len(all_scraped_texts)} 件）:")
            for idx, raw_txt in enumerate(all_scraped_texts):
                print(f"   [{idx}] {raw_txt}")
            
            # 前半4つをHOME、後半4つをAWAYへ分割
            home_texts = all_scraped_texts[:4]
            away_texts = all_scraped_texts[4:8]
            
            # 各チームの計算実行（デバッグ文を内包）
            home_status, home_coef, home_detail = analyze_recent_4(home_texts, home_team, is_home_top5, match_list, "HOME")
            away_status, away_coef, away_detail = analyze_recent_4(away_texts, away_team, is_away_top5, match_list, "AWAY")
            
            # 結果の要約出力
            print(f"\n 📝 【判定結果の確定】")
            print(f"   🏠 HOME {home_team}{' [★上位]' if is_home_top5 else ''}: {home_detail} -> 判定:{home_status} ({home_coef})")
            print(f"   🚀 AWAY {away_team}{' [★上位]' if is_away_top5 else ''}: {away_detail} -> 判定:{away_status} ({away_coef})")
            
        except Exception as e:
            err_msg = str(e).replace('\n', ' ')
            print(f"   ⚠️ エラー発生(試合No.{match_no}): {err_msg}")
            home_status, home_coef, home_detail = "普通", 0.0, "エラーにより判定不能"
            away_status, away_coef, away_detail = "普通", 0.0, "エラーにより判定不能"
        finally:
            context.close()
            
        # JSON反映
        match_data["homeCondition"] = home_status
        match_data["homeConditionCoef"] = home_coef
        match_data["awayCondition"] = away_status
        match_data["awayConditionCoef"] = away_coef
        
    browser.close()

# 4. 保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("\n💾 [teamCondition.py] デバッグ完全可視化版にて、data.json を最終保存しました！")
