import time
import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

TOP_URL = "https://www.totoone.jp/"

# =====================================================================
# 1️⃣ 左側の処理：チーム名と順位を取得してベースの器（リスト）を作る関数
# =====================================================================
def fetch_team_and_rank(match_ids):
    print("\n1️⃣ [左側の処理] チーム名・順位の取得ループを開始します...")
    match_list = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for idx, m_id in enumerate(match_ids, start=1):
            target_url = f"https://www.totoone.jp/match/{m_id}"
            print(f"✈️ [試合No.{idx}] チーム名・順位パース中... ({target_url})")
            
            context = browser.new_context(
                viewport={"width": 1280, "height": 1024},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 初期値のセット
            home_team = f"ホームチーム_{idx}"
            away_team = f"アウェイチーム_{idx}"
            home_rank = 99
            away_rank = 99
            
            try:
                # 確実にNext.jsの画面展開を待つため networkidle を指定
                page.goto(target_url, wait_until="networkidle", timeout=60000)
                time.sleep(2)  # 安全マージン
                
                html_content = page.content()
                soup = BeautifulSoup(html_content, "html.parser")
                
                # クラス名から要素を抽出
                teams = soup.find_all('div', class_='team-name')
                ranks = soup.find_all('span', class_='rank-number')
                
                if teams and len(teams) >= 2:
                    home_team = teams[0].get_text().strip()
                    away_team = teams[1].get_text().strip()
                
                if ranks and len(ranks) >= 2:
                    h_num = re.findall(r'\d+', ranks[0].get_text())
                    a_num = re.findall(r'\d+', ranks[1].get_text())
                    if h_num: home_rank = int(h_num[0])
                    if a_num: away_rank = int(a_num[0])
                    
            except Exception as e:
                print(f"   ⚠️ チーム名取得でエラーが発生しました(スキップします): {e}")
            finally:
                context.close()
                
            # 1試合分のデータを器に格納
            match_item = {
                "matchNo": idx,
                "holdId": m_id,  # 後続処理のために各試合の実IDを保持
                "homeTeam": home_team,
                "awayTeam": away_team,
                "homeRank": home_rank,
                "awayRank": away_rank,
                "homeInjuries": "なし",
                "awayInjuries": "なし",
                "homeInjuriesCount": 0,
                "awayInjuriesCount": 0
            }
            match_list.append(match_item)
            
        browser.close()
        
    return match_list


# =====================================================================
# 2️⃣ 右側の処理：既存の器（リスト）に対して、怪我人情報を追記する関数
# =====================================================================
def fetch_injuries(match_list):
    print("\n2️⃣ [右側の処理] 怪我人・離脱者情報の取得ループを開始します...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for idx, match_data in enumerate(match_list, start=1):
            # holdIdに保存しておいた実際の試合IDを使用
            m_id = match_data["holdId"]
            target_url = f"https://www.totoone.jp/match/{m_id}"
            print(f"✈️ [試合No.{idx}] 怪我人データパース中... ({target_url})")
            
            context = browser.new_context(
                viewport={"width": 1280, "height": 1024},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            home_injuries = []
            away_injuries = []
            
            try:
                page.goto(target_url, wait_until="networkidle", timeout=60000)
                time.sleep(2)  # 安全マージン
                
                html_content = page.content()
                soup = BeautifulSoup(html_content, "html.parser")
                
                # 怪我人抽出ロジック（右側のパースをそのまま移植）
                for div in soup.find_all('div'):
                    status_text = div.get_text().strip()
                    if status_text in ["出場微妙", "欠場濃厚", "出場停止"]:
                        parent_box = div.find_parent()
                        if parent_box:
                            tags = [t for t in parent_box.children if t.name is not None]
                            status_index = -1
                            for s_idx, t in enumerate(tags):
                                if t.get_text().strip() == status_text:
                                    status_index = s_idx
                                    break
                            
                            if status_index != -1:
                                # HOME側
                                for t in tags[:status_index]:
                                    for li in t.find_all('li'):
                                        txt = li.get_text().strip()
                                        p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                                        if p_match:
                                            name = p_match.group(1).strip()
                                            if name and name != "なし" and name not in home_injuries:
                                                home_injuries.append(name)
                                                
                                # AWAY側
                                for t in tags[status_index+1:]:
                                    for li in t.find_all('li'):
                                        txt = li.get_text().strip()
                                        p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                                        if p_match:
                                            name = p_match.group(1).strip()
                                            if name and name != "なし" and name not in away_injuries:
                                                away_injuries.append(name)
                                                
            except Exception as e:
                print(f"   ⚠️ 怪我人取得側でエラーが発生しました(スキップします): {e}")
            finally:
                context.close()

            # 文字列整形とカウント
            home_injuries_str = " / ".join(home_injuries) if home_injuries else "なし"
            away_injuries_str = " / ".join(away_injuries) if away_injuries else "なし"
            
            # 左側で作った器に怪我人データをマージ
            match_data["homeInjuries"] = home_injuries_str
            match_data["awayInjuries"] = away_injuries_str
            match_data["homeInjuriesCount"] = len(home_injuries)
            match_data["awayInjuriesCount"] = len(away_injuries)
            
            # コンソールに進捗と結果をわかりやすく表示
            print(f"   📊 確定結果 -> {match_data['homeTeam']}({match_data['homeRank']}位) vs {match_data['awayTeam']}({match_data['awayRank']}位)")
            print(f"   🚨 離脱追記 -> H {len(home_injuries)}人 ({home_injuries_str}) / A {len(away_injuries)}人 ({away_injuries_str})")
            
        browser.close()
        
    return match_list


# =====================================================================
# 🚀 メイン実行処理（ご提案いただいたタイムライン通りに実行）
# =====================================================================
if __name__ == "__main__":
    print("🔄 [関数化・完全分離版スクリプト] 起動中...")
    
    # 事前準備: トップページから13試合の最新IDを自動検出する（右側の仕組みを適用）
    print("🔎 トップページから本日の試合IDを抽出しています...")
    detected_ids = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(TOP_URL, wait_until="networkidle")
            html_top = page.content()
            # /match/数字 をすべて抽出
            all_ids = [int(x) for x in re.findall(r"/match/(\d+)", html_top)]
            if all_ids:
                base_id = min([idx for idx in all_ids if idx >= 27736])
                detected_ids = [base_id + i for i in range(13)]
        except Exception as e:
            print(f"⚠️ IDの自動抽出に失敗しました。固定値を使用します。 Error: {e}")
        finally:
            context.close()
            browser.close()

    # 万が一自動取得が空振った場合のセーフティ固定値
    if not detected_ids:
        detected_ids = [27736, 27737, 27738, 27739, 27740, 27741, 27742, 27743, 27744, 27745, 27746, 27747, 27748]

    print(f"運用の対象となる試合IDリスト: {detected_ids}")

    # -------------------------------------------------------------
    # ⭐ 提案いただいたメインフローの実行
    # -------------------------------------------------------------
    # 1. 左側()
    base_data_list = fetch_team_and_rank(detected_ids)
    
    # 2. sleep(3)
    print("\n⏳ チーム名取得（左側）が完了しました。3秒間待機します...")
    time.sleep(3)
    
    # 3. 右側()
    # final_data_list = fetch_injuries(base_data_list)
    
    # -------------------------------------------------------------
    # 成果物の保存
    # -------------------------------------------------------------
    # 保存する直前に、後続処理に不要な holdId を本来の1512（固定）などの運用値に戻すか消去
    for data in final_data_list:
        data["holdId"] = 1512  # 必要に応じて元の固定回コードに上書き
        
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data_list, f, ensure_ascii=False, indent=4)
        
    print("\n✨ [SUCCESS] すべてのデータが正常に統合され、data.json へ保存されました！")
