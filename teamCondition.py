import json
import re
import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

print("3️⃣ [teamCondition.py] 直近5試合のコンディション（裏ロジック救済あり）を計算して追記します...")

# 1. 既存の data.json を読み込む
if not os.path.exists('data.json'):
    print("❌ data.json が見つかりません！先に前段のスクリプトを実行してください。")
    exit(1)

with open('data.json', 'r', encoding='utf-8') as f:
    match_list = json.load(f)

# 2. 現在の1〜5位のチーム名を data.json から自動抽出してリスト化
top5_teams = set()
for m in match_list:
    # homeTeam と awayTeam の順位をチェックして1〜5位ならセットに追加
    if "homeRank" in m and m["homeRank"] <= 5:
        top5_teams.add(m["homeTeam"])
    if "awayRank" in m and m["awayRank"] <= 5:
        top5_teams.add(m["awayTeam"])

print(f"📊 現在の1〜5位チーム（救済対象）: {list(top5_teams)}")

# 固定の13試合IDリスト
match_ids = [27736, 27737, 27738, 27739, 27740, 27741, 27742, 27743, 27744, 27745, 27746, 27747, 27748]

def analyze_recent_5(lines, is_home=True):
    """
    直近5試合の行リストから [勝数, 分数, 負数, 上位への1点差負け試合数] をカウントする関数
    """
    wins, draws, losses, tough_losses = 0, 0, 0, 0
    
    # 上から5行（直近5試合）だけをループ処理
    for line in lines[:5]:
        text = line.get_text().strip()
        
        # 勝敗マークとスコア、対戦相手を大まかに抽出する正規表現
        # 例: "5/10 J1百年構想リーグ 第16節清水 ●1-2 (A)"
        match_symbol = re.search(r"([〇●△])", text)
        score_match = re.search(r"(\d+)-(\d+)", text)
        
        if not match_symbol:
            continue
            
        symbol = match_symbol.group(1)
        
        if symbol == "〇":
            wins += 1
        elif symbol == "△":
            draws += 1
        elif symbol == "●":
            losses += 1
            
            # 【裏ロジック判定】負け（●）の場合のみ詳細チェック
            if score_match:
                my_score = int(score_match.group(1))
                opp_score = int(score_match.group(2))
                point_diff = opp_score - my_score
                
                # 1点差負け、かつ対戦相手が1〜5位に含まれているか
                if point_diff == 1:
                    # テキスト内から1~5位のチーム名が含まれているか走査
                    for top_team in top5_teams:
                        if top_team in text:
                            tough_losses += 1
                            break
                            
    # 基本の調子判定（1〜5のルール）
    if wins >= 4:
        status = "良好"
    elif wins == 3:
        status = "良好" if draws >= 1 else "普通"
    elif wins == 2:
        status = "普通" if draws >= 1 else "悪化"
    elif wins == 1:
        status = "普通" if draws >= 2 else "悪化"
    else:  # 0勝
        status = "悪化"
        
    # 【裏ロジック救済】悪化判定からの引き上げ
    if status == "悪化":
        if wins == 0 and tough_losses >= 3:
            status = "普通"
            print(f"   ✨ 救済発動 (0勝ですが上位に1点差負けが{tough_losses}試合あるため『普通』に引き上げ)")
        elif wins > 0 and tough_losses >= 2:
            status = "普通"
            print(f"   ✨ 救済発動 ({wins}勝ですが上位に1点差負けが{tough_losses}試合あるため『普通』に引き上げ)")

    # 係数の割り当て
    coef = 0.0
    if status == "良好":
        coef = 0.2
    elif status == "悪化":
        coef = -0.5
        
    return status, coef, f"{wins}勝{draws}分{losses}敗(救済対象:{tough_losses}試合)"

# 3. スクレイピング開始
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
            
            # 「今シーズンの成績」の下にあるテーブルの行（trまたはli等）を抽出
            # 左右の背景色（薄い赤/薄い青）のセル、または行をまとめて取得
            # トトワンの構造上、各成績はテーブル行か特定のコンテナに入っています
            # スクリーンショットに基づき、テキストが含まれるセクションを特定
            tables = soup.find_all('table')
            
            home_lines = []
            away_lines = []
            
            # 簡易的にテキスト構造から左右のデータを分離するロジック
            # 「今シーズンの成績」という文字列を含むセクションの下を探す
            sections = soup.find_all(lambda tag: tag.name in ['div', 'tr'] and "今シーズンの成績" in tag.get_text())
            
            # スクリーンの表から行を全スキャン
            for tr in soup.find_all('tr'):
                cells = tr.find_all('td')
                if len(cells) >= 2:
                    # 左セル（HOME）と右セル（AWAY）にそれぞれ試合結果のテキストがある場合
                    h_txt = cells[0].get_text().strip()
                    a_txt = cells[1].get_text().strip()
                    if "J1" in h_txt or "〇" in h_txt or "●" in h_txt or "△" in h_txt:
                        home_lines.append(cells[0])
                    if "J1" in a_txt or "〇" in a_txt or "●" in a_txt or "△" in a_txt:
                        away_lines.append(cells[1])
            
            # 万が一trで取れなかった場合の汎用パース（div構造用）
            if not home_lines:
                for div in soup.find_all('div'):
                    txt = div.get_text().strip()
                    if ("〇" in txt or "●" in txt or "△" in txt) and "第" in txt:
                        # ざっくり左側か右側かを配置で簡易判定、または親要素で分離
                        # ここは実際のHTMLに合わせtr判定をメインとします
                        pass

            # HOMEとAWAYの直近5試合を分析
            home_status, home_coef, home_detail = analyze_recent_5(home_lines, is_home=True)
            away_status, away_coef, away_detail = analyze_recent_5(away_lines, is_home=False)
            
        except Exception as e:
            print(f"   ⚠️ エラー(試合No.{match_no}): {e}")
            home_status, home_coef, home_detail = "普通", 0.0, "データ取得エラー"
            away_status, away_coef, away_detail = "普通", 0.0, "データ取得エラー"
        finally:
            context.close()
            
        # JSONデータに反映
        match_data["homeCondition"] = home_status
        match_data["homeConditionCoef"] = home_coef
        match_data["awayCondition"] = away_status
        match_data["awayConditionCoef"] = away_coef
        
        print(f"   🏠 HOME {match_data['homeTeam']}: {home_detail} -> 判定:{home_status} ({home_coef})")
        print(f"   🚀 AWAY {match_data['awayTeam']}: {away_detail} -> 判定:{away_status} ({away_coef})")
        print("-" * 50)
        
    browser.close()

# 4. 最終保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("💾 [teamCondition.py] コンディション情報の追記が完了し、data.json を最終保存しました！")
