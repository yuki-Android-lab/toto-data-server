import time
import json
import re
import os
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# 固定の13試合IDリスト
match_ids = [27736, 27737, 27738, 27739, 27740, 27741, 27742, 27743, 27744, 27745, 27746, 27747, 27748]
match_list = []

print("🔄 [2ステップ完全分離] 13試合分のチーム名取得ループを実行後、待機を挟んでから怪我人取得ループを実行します...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # =====================================================================
    # 🌟 【ステップ1】for(13試合分) チーム名・順位取得ループ
    # =====================================================================
    print("\n1️⃣ [チーム名・順位の取得ループを開始します]")
    for idx, m_id in enumerate(match_ids, start=1):
        target_url = f"https://www.totoone.jp/match/{m_id}"
        print(f"✈️ [試合No.{idx}] チーム名・順位パース中... ({target_url})")
        
        context1 = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page1 = context1.new_page()
        
        home_team = f"ホームチーム_{idx}"
        away_team = f"アウェイチーム_{idx}"
        home_rank = 99
        away_rank = 99
        
        try:
            # 左側の接続形式（domcontentloaded でチーム名を最優先取得）
            page1.goto(target_url, wait_until="domcontentloaded")
            html_content1 = page1.content()
            soup1 = BeautifulSoup(html_content1, "html.parser")
            
            # WinMerge左側のチーム名・順位パース
            teams = soup1.find_all('div', class_='team-name')
            ranks = soup1.find_all('span', class_='rank-number')
            
            if teams and len(teams) >= 2:
                home_team = teams[0].get_text().strip()
                away_team = teams[1].get_text().strip()
            
            if ranks and len(ranks) >= 2:
                h_num = re.findall(r'\d+', ranks[0].get_text())
                a_num = re.findall(r'\d+', ranks[1].get_text())
                if h_num: home_rank = int(h_num[0])
                if a_num: away_rank = int(a_num[0])
                
        except Exception as e:
            print(f"   ⚠️ チーム名取得でエラー: {e}")
        finally:
            context1.close()
            
        # まずはチーム名と順位だけの辞書を作ってリストに追加
        match_item = {
            "matchNo": idx,
            "holdId": 1512, # 開催回ID
            "homeTeam": home_team,
            "awayTeam": away_team,
            "homeRank": home_rank,
            "awayRank": away_rank,
            "homeInjuries": "なし",  # 後で上書きするため初期化
            "awayInjuries": "なし",  # 後で上書きするため初期化
            "homeInjuriesCount": 0,
            "awayInjuriesCount": 0
        }
        match_list.append(match_item)

    # =====================================================================
    # 🌟 【ステップ2】ループ外での sleep(3)
    # =====================================================================
    print("\n⏳ 13試合分のチーム名取得が完了しました。3秒間待機します...")
    time.sleep(3)

    # =====================================================================
    # 🌟 【ステップ3】for(13試合分) 怪我人取得ループ
    # =====================================================================
    print("\n2️⃣ [怪我人・離脱者情報の取得ループを開始します]")
    for idx, m_id in enumerate(match_ids, start=1):
        target_url = f"https://www.totoone.jp/match/{m_id}"
        print(f"✈️ [試合No.{idx}] 怪我人データパース中... ({target_url})")
        
        context2 = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page2 = context2.new_page()
        
        home_injuries = []
        away_injuries = []
        
        try:
            # 右側の接続形式（networkidle でJavaScript展開を完全に待つ）
            page2.goto(target_url, wait_until="networkidle", timeout=60000)
            time.sleep(2) # 描画安全マージン
            html_content2 = page2.content()
            soup2 = BeautifulSoup(html_content2, "html.parser")
            
            # WinMerge右側の怪我人パースロジック
            for div in soup2.find_all('div'):
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
            print(f"   ⚠️ 怪我人取得側でエラー: {e}")
        finally:
            context2.close()

        home_injuries_str = " / ".join(home_injuries) if home_injuries else "なし"
        away_injuries_str = " / ".join(away_injuries) if away_injuries else "なし"
        
        # ステップ1で作成した13試合分のリストデータに、怪我人情報をインデックスで紐づけて追記
        match_list[idx - 1]["homeInjuries"] = home_injuries_str
        match_list[idx - 1]["awayInjuries"] = away_injuries_str
        match_list[idx - 1]["homeInjuriesCount"] = len(home_injuries)
        match_list[idx - 1]["awayInjuriesCount"] = len(away_injuries)
        
        # 途中経過の確定ログ出力
        h_team = match_list[idx - 1]["homeTeam"]
        a_team = match_list[idx - 1]["awayTeam"]
        h_rank = match_list[idx - 1]["homeRank"]
        a_rank = match_list[idx - 1]["awayRank"]
        print(f"   📊 確定結果 -> {h_team}({h_rank}位) vs {a_team}({a_rank}位)")
        print(f"   🚨 離脱追記 -> H {len(home_injuries)}人 ({home_injuries_str}) / A {len(away_injuries)}人 ({away_injuries_str})")

    browser.close()

# =====================================================================
# 🌟 【ステップ4】JSON書込み & END
# =====================================================================
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("\n✨ [END] すべてのデータが正常に data.json へ統合保存されました！")
