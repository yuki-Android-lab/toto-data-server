import json
import re
import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

if not os.path.exists('data.json'):
    print("❌ data.json が見つかりません！先に fetch_toto.py を実行してください。")
    exit(1)

with open('data.json', 'r', encoding='utf-8') as f:
    match_list = json.load(f)

print("🔄 [test_scrape] 既存の data.json に離脱者情報を追記します...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    for match_data in match_list:
        match_no = match_data["matchNo"]
        base_match_id = match_data["holdId"]
        
        # URL構造の担保
        target_url = f"https://www.totoone.jp/match/{base_match_id + (match_no - 1)}"
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # --- 修正①：Next.jsの描画を確実に待つ ---
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            # レンダリング安全マージンとして2秒静止
            time.sleep(2)
            
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            home_injuries = []
            away_injuries = []
            
            # --- 離脱者情報の取得（現代版アップデート） ---
            # ページ内のすべての「li（選手が並ぶリスト）」を網羅する
            for li in soup.find_all('li'):
                txt = li.get_text().strip()
                
                # 修正②：完全一致ではなく、テキストの中にキーワードが含まれているか（部分一致）で判定
                if any(k in txt for k in ["出場微妙", "欠場濃厚", "出場停止", "欠場"]):
                    # ポジション（GK/DF/MF/FW）と選手名を正規表現で分離
                    p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                    if p_match:
                        name = p_match.group(1).strip()
                        if name and name != "なし":
                            # サイトの構造上、ホームとアウェイの判別は、親要素の並び順か
                            # あるいはそのliが「何番目のブロック」にあるかで判別するのが最も安全です。
                            # ここでは安全に、見つかった選手がどちらの所属エリアにいるかをDOMツリーを遡って判定します。
                            
                            # 該当するliの祖先を遡り、チームの左右を特定するためのアプローチ
                            parent_text = ""
                            p_node = li.find_parent('section')
                            if p_node:
                                parent_text = p_node.get_text()
                            
                            # もしsectionで見つからなければ、周辺のテキストから推測
                            if not parent_text:
                                p_node = li.find_parent('div')
                                if p_node:
                                    parent_text = p_node.get_text()

                            # 暫定的に、最初のキーワード発見順、または従来の配列に安全に振り分け
                            # ※ より厳密には、見つかったテキストを順次格納
                            # 昔のロジックが期待する「配列への追加」を担保
                            if "ホーム" in parent_text or "HOME" in parent_text:
                                if name not in home_injuries:
                                    home_injuries.append(name)
                            elif "アウェイ" in parent_text or "AWAY" in parent_text:
                                if name not in away_injuries:
                                    away_injuries.append(name)
                            else:
                                # 判別がつかない場合は、昔のロジックの「前半/後半」の挙動に合わせ、
                                # ひとまずhome側に入れておき、ログで目視できるようにします
                                if name not in home_injuries and name not in away_injuries:
                                    home_injuries.append(name)

            # 万が一上のロジックですり抜けた場合のための、昔の「div一括検索」の強化版バックアップ
            if not home_injuries and not away_injuries:
                for div in soup.find_all('div'):
                    status_text = div.get_text().strip()
                    if any(k in status_text for k in ["出場微妙", "欠場濃厚", "出場停止"]):
                        parent_box = div.find_parent()
                        if parent_box:
                            for li in parent_box.find_all('li'):
                                txt = li.get_text().strip()
                                p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                                if p_match:
                                    name = p_match.group(1).strip()
                                    if name and name != "なし" and name not in home_injuries:
                                        home_injuries.append(name)

            home_injuries_str = " / ".join(home_injuries) if home_injuries else "なし"
            away_injuries_str = " / ".join(away_injuries) if away_injuries else "なし"
            
            # 既存の完璧なチーム名データを壊さずに、離脱者情報だけを上書き
            match_data["homeInjuries"] = home_injuries_str
            match_data["awayInjuries"] = away_injuries_str
            match_data["homeInjuriesCount"] = len(home_injuries)
            match_data["awayInjuriesCount"] = len(away_injuries)
            
            h_team = match_data.get("homeTeam")
            a_team = match_data.get("awayTeam")
            h_rank = match_data.get("homeRank")
            a_rank = match_data.get("awayRank")
            
            print(f"🌐 [試合No.{match_no}] {h_team}({h_rank}位) vs {a_team}({a_rank}位)")
            print(f"   👉 離脱追記: H {len(home_injuries)}人 ({home_injuries_str}) / A {len(away_injuries)}人 ({away_injuries_str})")

        except Exception as e:
            print(f"⚠️ 試合No.{match_no} 離脱者取得エラー（スキップします）: {e}")
            
        context.close()

    browser.close()

# 最終統合データを上書き保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("✨ 離脱者データの追記・統合がすべて正常に完了しました！")
