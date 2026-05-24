import json
import re
import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

print("3️⃣ [teamCondition.py] liタグ＆スコア数字基準で直近5試合のコンディションを正確に計算します...")

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

def analyze_recent_5_from_texts(text_list, team_name, is_self_top5, match_list):
    """
    抽出した文字列リスト（直近5試合）からスコアの数字だけで勝・分・敗をガチ判定する
    """
    wins, draws, losses, tough_losses = 0, 0, 0, 0
    processed_count = 0
    
    for txt in text_list[:5]:
        score_match = re.search(r"(\d+)-(\d+)", txt)
        if not score_match:
            continue
            
        processed_count += 1
        my_score = int(score_match.group(1))   # 自チーム得点
        opp_score = int(score_match.group(2))  # 相手チーム得点
        
        # 💡 スコアの数字だけで勝敗を再定義（PK戦の〇●を排除）
        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            draws += 1
        else:
            losses += 1
            
            # 【裏ロジック救済判定】
            # 自身が1〜5位でなく、かつ1点差負けの場合のみ
            if not is_self_top5 and (opp_score - my_score) == 1:
                # スコアの文字より前にある「〇〇第16節清水」のような文字列から相手を特定
                opp_part = txt.split(score_match.group(0))[0]
                if check_if_opponent_is_top5(opp_part, match_list):
                    tough_losses += 1

    if processed_count == 0:
        return "普通", 0.0, "0勝0分0敗(戦績テキストなし)"

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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, http Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            time.sleep(2)
            html_content = page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            
            # 1〜5位フラグ
            is_home_top5 = get_top5_status(match_data['homeTeam'], match_list)
            is_away_top5 = get_top5_status(match_data['awayTeam'], match_list)
            
            # 💡 ページ内の全 <li> タグから戦績テキストだけを一列に全回収
            valid_li_texts = []
            for li in soup.find_all('li'):
                txt = li.get_text().strip().replace('\n', ' ')
                # 日付（/）とスコア（-）が含まれる行を本物の戦績と見なす
                if "/" in txt and re.search(r"\d+-\d+", txt):
                    if txt not in valid_li_texts:
                        valid_li_texts.append(txt)
            
            # 💡 データの分配ロジック
            # トトワンは「今シーズンの成績」として、左側にHOMEの直近試合、右側にAWAYの直近試合が並ぶ。
            # HTML的には、HOME側の戦績が何件か連続したあと、AWAY側の戦績が何件か連続する。
            # 確実に分離するため、日付が最新から過去に遡る「切れ目（日付の逆転）」を検知して分離する。
            home_texts = []
            away_texts = []
            
            is_switching_to_away = False
            last_month = 13
            
            for t in valid_li_texts:
                # テキストから月（例: 5/10 の 5）を抜く
                month_match = re.search(r"(\d+)/", t)
                if month_match:
                    current_month = int(month_match.group(1))
                    # 日付が急に未来に戻ったら、そこからAWAYチームのデータに切り替わった証拠
                    if current_month > last_month and len(home_texts) >= 3:
                        is_switching_to_away = True
                    last_month = current_month
                
                if not is_switching_to_away:
                    home_texts.append(t)
                else:
                    away_texts.append(t)
            
            # 各チームの計算実行
            home_status, home_coef, home_detail = analyze_recent_5_from_texts(home_texts, match_data['homeTeam'], is_home_top5, match_list)
            away_status, away_coef, away_detail = analyze_recent_5_from_texts(away_texts, match_data['awayTeam'], is_away_top5, match_list)
            
        except Exception as e:
            print(f"   ⚠️ エラー(試合No.{match_no}): {e}")
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
        
        print(f"   🏠 HOME {match_data['homeTeam']}{h_tag}: {home_detail} -> 判定:{home_status} ({home_coef})")
        print(f"   🚀 AWAY {match_data['awayTeam']}{a_tag}: {away_detail} -> 判定:{away_status} ({away_coef})")
        print("-" * 50)
        
    browser.close()

# 4. 保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("💾 [teamCondition.py] liタグ完全スキャン版にて、data.json を最終保存しました！")
