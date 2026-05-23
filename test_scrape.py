import time
import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

TOP_URL = "https://www.totoone.jp/"
match_list = []

print("🔄 ブラウザを起動して最新のtotoデータを同期します...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # 1. 最新の開催回の基準IDを自動抽出
    base_match_id = 27736 
    try:
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        init_page = context.new_page()
        init_page.goto(TOP_URL, wait_until="networkidle")
        html_top = init_page.content()
        match_ids = [int(x) for x in re.findall(r"/match/(\d+)", html_top)]
        if match_ids:
            # 27736以上のIDの中で最も小さいものを基準にする
            base_match_id = min([idx for idx in match_ids if idx >= 27736])
        context.close()
    except Exception as e:
        print(f"⚠️ 基準ID自動抽出中の警告（処理は続行します）: {e}")

    print(f"🎯 検出した第1試合URLのID: {base_match_id}")

    # 2. 13試合の解析（try-exceptでのデータ隠蔽を完全撤廃）
    for i in range(13):
        match_no = i + 1
        target_url = f"https://www.totoone.jp/match/{base_match_id + i}"
        print(f"🔗 [試合No.{match_no}] 接続中... URL: {target_url}")
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 💡あえてエラーをそのまま発生させます
        page.goto(target_url, wait_until="networkidle")
        time.sleep(2.0)
        
        html_content = page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # --- ① チーム名と順位の取得 ---
        card_area = soup.select_one('div[class*="Detail_matchCard__"]')
        if not card_area:
            # そもそもページ構造が違う、あるいはロードできていない場合はここで明示的に例外を投げます
            raise ValueError(f"試合No.{match_no} の対戦カードエリア（Detail_matchCard__）がHTML内に見つかりません。ロード失敗かURLが間違っている可能性があります。")
            
        card_text = card_area.get_text()
        teams = re.findall(r"([^\s\d位勝点]+?)\s*(?:VS|ｖｓ)\s*([^\s\d位勝点キックオフ]+)", card_text)
        if not teams:
            raise ValueError(f"対戦カードテキスト '{card_text}' からチーム名をパースできませんでした。")
            
        home_team = teams[0][0].strip()
        away_team = teams[0][1].strip()
        
        # 順位
        rank_elements = soup.select('p[class*="Detail_rank__"]')
        if len(rank_elements) < 2:
            print(f"⚠️ 順位要素（Detail_rank__）が2つ見つかりません。現在の検出数: {len(rank_elements)}")
            home_rank, away_rank = 10, 10
        else:
            h_r = re.search(r"\d+", rank_elements[0].get_text())
            a_r = re.search(r"\d+", rank_elements[1].get_text())
            home_rank = int(h_r.group()) if h_r else 10
            away_rank = int(a_r.group()) if a_r else 10

        # --- ② 離脱者情報の取得 ---
        home_injuries = []
        away_injuries = []
        
        info_blocks = soup.select('div[class*="Detail_playerInfo__"]')
        
        for block in info_blocks:
            status_tag = block.select_one('[class*="Detail_memberInfo__"]')
            if not status_tag:
                continue
            status_text = status_tag.get_text().strip()
            
            if status_text in ["出場微妙", "欠場濃厚", "出場停止"]:
                # ホーム
                home_box = block.select_one('[class*="Detail_home__"]')
                if home_box:
                    for li in home_box.select('li'):
                        txt = li.get_text().strip()
                        p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                        if p_match:
                            name = p_match.group(1).strip()
                            if name and name != "なし" and name not in home_injuries:
                                home_injuries.append(name)
                                
                # アウェイ
                away_box = block.select_one('[class*="Detail_away__"]')
                if away_box:
                    for li in away_box.select('li'):
                        txt = li.get_text().strip()
                        p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                        if p_match:
                            name = p_match.group(1).strip()
                            if name and name != "なし" and name not in away_injuries:
                                away_injuries.append(name)

        home_injuries_str = " / ".join(home_injuries) if home_injuries else "なし"
        away_injuries_str = " / ".join(away_injuries) if away_injuries else "なし"
        
        print(f"🌐 [試合No.{match_no}] {home_team}({home_rank}位) vs {away_team}({away_rank}位)")
        print(f"  👉 離脱: H {len(home_injuries)}人 ({home_injuries_str}) / A {len(away_injuries)}人 ({away_injuries_str})")

        context.close()

    browser.close()
