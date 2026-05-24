import json
import re
import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

print("3️⃣ [teamCondition.py] カラム構造からHOMEとAWAYを完璧に分離します（バグ修正版）...")

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

    # 4試合基準のトレンドマッピング
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
            print(f"   ✨ 救済発動 [{team_name}]: 直近4戦で上位へ1点差負けが{tough_losses}試合あるため『普通』に引き上げ")

    coef = 0.0
    if status == "良好":
        coef = 0.2
    elif status == "悪化":
        coef = -0.5
        
    return status, coef, f"{wins}勝{draws}分{losses}敗(直近{processed_count}試合ベース / 上位への1点差負け:{tough_losses})"


# 3. スクレイピングメイン処理
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    for i, match_data in enumerate(match_list):
        match_no = match_data["matchNo"]
        m_id = match_ids[i]
        
        home_team = match_data['homeTeam']
        away_team = match_data['awayTeam']
        
        target_url = f"https://www.totoone.jp/match/{m_id}"
        print(f"✈️ コンディション解析中 (試合No.{match_no}): {home_team} vs {away_team}")
        
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
            
            home_texts = []
            away_texts = []
            
            # 💡 【本線ロジック】行（tr）を走査し、左セル（HOME）と右セル（AWAY）を完全分離
            for tr in soup.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 2:
                    td_left = tds[0].get_text().strip().replace('\n', ' ')
                    td_right = tds[1].get_text().strip().replace('\n', ' ')
                    
                    if "/" in td_left and re.search(r"\d+-\d+", td_left):
                        home_texts.append(td_left)
                    if "/" in td_right and re.search(r"\d+-\d+", td_right):
                        away_texts.append(td_right)
            
            # 💡 【バックアップ】万が一tableで拾えなかった場合、liのクラス属性（背景色）から安全に拾う（エラー修正済）
            if not home_texts or not away_texts:
                home_texts = []
                away_texts = []
                for li in soup.find_all('li'):
                    txt = li.get_text().strip().replace('\n', ' ')
                    if "/" in txt and re.search(r"\d+-\d+", txt):
                        # 安全にクラス名を取得（文字列化）
                        cls_list = li.get('class', [])
                        cls_str = "".join(cls_list) if isinstance(cls_list, list) else str(cls_list)
                        
                        if 'home' in cls_str or 'pink' in cls_str:
                            home_texts.append(txt)
                        elif 'away' in cls_str or 'blue' in cls_str:
                            away_texts.append(txt)
            
            # 💡 【最終防衛】どちらも空なら機械的2等分
            if not home_texts or not away_texts:
                all_lis = []
                for li in soup.find_all('li'):
                    txt = li.get_text().strip().replace('\n', ' ')
                    if "/" in txt and re.search(r"\d+-\d+", txt):
                        if txt not in all_lis:
                            all_lis.append(txt)
                half = len(all_lis) // 2
                home_texts = all_lis[:half]
                away_texts = all_lis[half:]

            # 各チームの計算実行
            home_status, home_coef, home_detail = analyze_recent_4(home_texts, home_team, is_home_top5, match_list)
            away_status, away_coef, away_detail = analyze_recent_4(away_texts, away_team, is_away_top5, match_list)
            
        except Exception as e:
            err_msg = str(e).replace('\n', ' ')
            print(f"   ⚠️ エラー(試合No.{match_no}): {err_msg}")
            home_status, home_coef, home_detail = "普通", 0.0, "エラーにより判定不能"
            away_status, away_coef, away_detail = "普通", 0.0, "エラーにより判定不能"
        finally:
            context.close()
            
        # JSON反映
        match_data["homeCondition"] = home_status
        match_data["homeConditionCoef"] = home_coef
        match_data["awayCondition"] = away_status
        match_data["awayConditionCoef"] = away_coef
        
        h_tag = " [★現在1~5位]" if is_home_top5 else ""
        a_tag = " [★現在1~5位]" if is_away_top5 else ""
        
        print(f"   🏠 HOME {home_team}{h_tag}: {home_detail} -> 判定:{home_status} ({home_coef})")
        print(f"   🚀 AWAY {away_team}{a_tag}: {away_detail} -> 判定:{away_status} ({away_coef})")
        print("-" * 50)
        
    browser.close()

# 4. 保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("💾 [teamCondition.py] エラー修正・カラム構造分離型にて、data.json を最終保存しました！")
