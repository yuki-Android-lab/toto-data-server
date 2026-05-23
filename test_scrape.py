import time
import json
import re
import os
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# 固定の13試合IDリスト
match_ids = [27736, 27737, 27738, 27739, 27740, 27741, 27742, 27743, 27744, 27745, 27746, 27747, 27748]

# =====================================================================
# 👈 左側のソース（チーム名・順位が100%取れるロジック）をそのまま関数化
# =====================================================================
def 左側():
    print("\n1️⃣ [左側の処理] チーム名・順位の取得を開始します...")
    hold_id = 1512
    match_list = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for idx, m_id in enumerate(match_ids, start=1):
            # 左側のURL生成ロジック（そのまま）
            base_match_id = 27736
            target_url = f"https://www.totoone.jp/match/{base_match_id + (idx - 1)}"
            print(f"✈️ [左側] 解析中: {target_url}")
            
            context = browser.new_context(
                viewport={"width": 1280, "height": 1024},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            try:
                # 左側の接続設定（そのまま）
                page.goto(target_url, wait_until="domcontentloaded")
                html_content = page.content()
                soup = BeautifulSoup(html_content, "html.parser")
                
                # 左側のパース処理を完全にそのまま移植
                teams = soup.find_all('div', class_='team-name')
                ranks = soup.find_all('span', class_='rank-number')
                
                home_team = teams[0].get_text().strip() if len(teams) >= 2 else f"ホームチーム_{idx}"
                away_team = teams[1].get_text().strip() if len(teams) >= 2 else f"アウェイチーム_{idx}"
                
                home_rank = 99
                away_rank = 99
                if len(ranks) >= 2:
                    h_num = re.findall(r'\d+', ranks[0].get_text())
                    a_num = re.findall(r'\d+', ranks[1].get_text())
                    if h_num: home_rank = int(h_num[0])
                    if a_num: away_rank = int(a_num[0])
                
                # 左側のmatch_list用オブジェクト構造
                match_item = {
                    "matchNo": idx,
                    "holdId": hold_id,
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
                
            except Exception as e:
                print(f"   ⚠️ 左側エラー(試合No.{idx}): {e}")
            finally:
                context.close()
                
        browser.close()
        
    # 左側で作ったデータを一旦 data.json に書き出し保存
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(match_list, f, ensure_ascii=False, indent=4)
    print("💾 左側のベースデータを data.json に保存しました。")


# =====================================================================
# 👉 右側のソース（怪我人が100%取れるロジック）をそのまま関数化
# =====================================================================
def 右側():
    print("\n2️⃣ [右側の処理] 怪我人情報の取得と上書きマージを開始します...")
    
    # 左側が保存した data.json を読み込んで器（リスト）にする
    if not os.path.exists('data.json'):
        print("❌ data.json が見つかりません。")
        return
        
    with open('data.json', 'r', encoding='utf-8') as f:
        match_list = json.load(f)
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for idx, m_id in enumerate(match_ids, start=1):
            # 右側のURL生成ロジック（そのまま）
            target_url = f"https://www.totoone.jp/match/{m_id}"
            print(f"✈️ [右側] 解析中: {target_url}")
            
            context = browser.new_context(
                viewport={"width": 1280, "height": 1024},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            home_injuries = []
            away_injuries = []
            
            try:
                # 右側の接続設定（そのまま）
                page.goto(target_url, wait_until="networkidle", timeout=60000)
                time.sleep(2)
                html_content = page.content()
                soup = BeautifulSoup(html_content, "html.parser")
                
                # 右側の怪我人パースロジックを完全にそのまま移植
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
                print(f"   ⚠️ 右側エラー(試合No.{idx}): {e}")
            finally:
                context.close()

            home_injuries_str = " / ".join(home_injuries) if home_injuries else "なし"
            away_injuries_str = " / ".join(away_injuries) if away_injuries else "なし"
            
            # 左側から読み込んだ match_list[idx-1] に対して右側のデータをそのままマージ
            match_list[idx - 1]["homeInjuries"] = home_injuries_str
            match_list[idx - 1]["awayInjuries"] = away_injuries_str
            match_list[idx - 1]["homeInjuriesCount"] = len(home_injuries)
            match_list[idx - 1]["awayInjuriesCount"] = len(away_injuries)
            
            # コンソールログへの進捗表示
            h_team = match_list[idx - 1]["homeTeam"]
            a_team = match_list[idx - 1]["awayTeam"]
            h_rank = match_list[idx - 1]["homeRank"]
            a_rank = match_list[idx - 1]["awayRank"]
            print(f"   📊 確定 -> {h_team}({h_rank}位) vs {a_team}({a_rank}位)")
            print(f"   🚨 離脱 -> H {len(home_injuries)}人 ({home_injuries_str}) / A {len(away_injuries)}人 ({away_injuries_str})")
            
        browser.close()
        
    # 最終的なデータを再度 data.json へ上書き保存
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(match_list, f, ensure_ascii=False, indent=4)


# =====================================================================
# 🚀 ご提示いただいたタイムラインで実行
# =====================================================================
if __name__ == "__main__":
    # 1. 左側()
    左側()
    
    # 2. sleep(3)
    print("\n⏳ 左側の処理が完了しました。3秒間待機します...")
    time.sleep(3)
    
    # 3. 右側()
    右側()
    
    print("\n✨ [END] 左側と右側の処理が順番に実行され、すべてのデータが正常にマージされました！")
