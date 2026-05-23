import json
import re
import os
import sys
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# ==============================================================================
# 1. 各種バリデーション＆データ標準化関数
# ==============================================================================
def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()

def get_only_digits(text: str) -> int:
    nums = re.findall(r'\d+', text)
    return int(nums[0]) if nums else 0

# ==============================================================================
# 2. 詳細スタッツ・対戦履歴パース関数群（ステップ数を肥大化させていた原因）
# ==============================================================================
def parse_match_history_block(soup: BeautifulSoup, block_index: int) -> list:
    history_data = []
    blocks = soup.find_all('div', class_='match-history-box')
    if len(blocks) > block_index:
        rows = blocks[block_index].find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                history_data.append({
                    "date": clean_text(cols[0].get_text()),
                    "opponent": clean_text(cols[1].get_text()),
                    "result": clean_text(cols[2].get_text()),
                    "score": clean_text(cols[3].get_text())
                })
    return history_data

def parse_team_performance_matrix(soup: BeautifulSoup) -> dict:
    matrix = {
        "home_attack": "0.0", "home_defense": "0.0",
        "away_attack": "0.0", "away_defense": "0.0"
    }
    containers = soup.find_all('div', class_='performance-matrix')
    if len(containers) >= 2:
        # ホーム側スタッツ
        h_scores = containers[0].find_all('span', class_='stat-value')
        if len(h_scores) >= 2:
            matrix["home_attack"] = clean_text(h_scores[0].get_text())
            matrix["home_defense"] = clean_text(h_scores[1].get_text())
        # アウェイ側スタッツ
        a_scores = containers[1].find_all('span', class_='stat-value')
        if len(a_scores) >= 2:
            matrix["away_attack"] = clean_text(a_scores[0].get_text())
            matrix["away_defense"] = clean_text(a_scores[1].get_text())
    return matrix

# ==============================================================================
# 3. 基本情報（チーム名・順位）パース関数
#    ※ 当時、クラス名のミスマッチでValueErrorを出して強制終了していた箇所
# ==============================================================================
def parse_basic_info(soup: BeautifulSoup, hold_id: int, match_no: int) -> dict:
    # 当時チーム名が取れずに崩壊していた古いクラス名セレクタ
    home_zone = soup.find('div', class_='team-home-display')
    away_zone = soup.find('div', class_='team-away-display')
    
    if not home_zone or not away_zone:
        # 旧サイトの代替クラス名でのフォールバック試行
        home_zone = soup.find('div', class_='left-team')
        away_zone = soup.find('div', class_='right-team')

    if not home_zone or not away_zone:
        raise ValueError(f"❌ [試合No.{match_no}] チーム情報(HOME/AWAY)のラッパーDIV要素が検知できません。")

    h_name_el = home_zone.find('h2') or home_zone.find('div', class_='name')
    a_name_el = away_zone.find('h2') or away_zone.find('div', class_='name')
    
    h_rank_el = home_zone.find('span', class_='rank') or home_zone.find('em')
    a_rank_el = away_zone.find('span', class_='rank') or away_zone.find('em')

    if not h_name_el or not a_name_el:
        raise ValueError(f"❌ [試合No.{match_no}] クラス名構造の変化により、チーム名文字列を抽出できません。")

    return {
        "holdId": hold_id,
        "matchNo": match_no,
        "homeTeam": clean_text(h_name_el.get_text()),
        "awayTeam": clean_text(a_name_el.get_text()),
        "homeRank": get_only_digits(h_rank_el.get_text()) if h_rank_el else 99,
        "awayRank": get_only_digits(a_rank_el.get_text()) if a_rank_el else 99
    }

# ==============================================================================
# 4. メインスクリプト実行コア
# ==============================================================================
def main():
    hold_id = 1512
    # 対戦詳細URLを生成するための13試合固有IDリスト
    match_ids = [27736, 27737, 27738, 27739, 27740, 27741, 27742, 27743, 27744, 27745, 27746, 27747, 27748]
    
    print(f"🔄 開催回 ID: {hold_id} の全13試合に対して 『完全独立ペア抽出』 を実行します...")
    
    # 既存のdata.json（前段のfetch_toto.pyの成果物）を読み込み
    if not os.path.exists('data.json'):
        print("❌ data.json が見つかりません！先に fetch_toto.py を実行してください。")
        sys.exit(1)
        
    with open('data.json', 'r', encoding='utf-8') as f:
        match_list = json.load(f)

    final_results = []

    with sync_playwright() as p:
        # 完全ヘッドレスで起動
        browser = p.chromium.launch(headless=True)
        
        for idx, m_id in enumerate(match_ids, start=1):
            target_url = f"https://www.totoone.jp/match/{m_id}"
            print(f"✈️ [試合No.{idx}] 解析中: {target_url}")
            
            context = browser.new_context(
                viewport={"width": 1280, "height": 1024},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            try:
                # 【重要】当時のロードタイミング設定（domcontentloaded）
                page.goto(target_url, wait_until="domcontentloaded")
                html_content = page.content()
                
                # 当時の指定に従い、lxmlパーサーでパース
                try:
                    soup = BeautifulSoup(html_content, "lxml")
                except:
                    soup = BeautifulSoup(html_content, "html.parser")
                
                # --- 基本情報のマージ処理 ---
                # 当時ここでValueErrorを出してワークフローを殺していたため、
                # data.jsonの既存データを引き継ぐためのキャッチブロック
                try:
                    basic_info = parse_basic_info(soup, hold_id, idx)
                except ValueError:
                    # 壊れたパースをスルーし、既存のdata.jsonからチーム名と順位をサルベージする
                    basic_info = None
                    for fallback_item in match_list:
                        if fallback_item.get("matchNo") == idx:
                            basic_info = {
                                "holdId": hold_id,
                                "matchNo": idx,
                                "homeTeam": fallback_item.get("homeTeam", f"チーム{idx}H"),
                                "awayTeam": fallback_item.get("awayTeam", f"チーム{idx}A"),
                                "homeRank": fallback_item.get("homeRank", 99),
                                "awayRank": fallback_item.get("awayRank", 99)
                            }
                            break
                    if not basic_info:
                        basic_info = {"holdId": hold_id, "matchNo": idx, "homeTeam": "Unknown", "awayTeam": "Unknown", "homeRank": 99, "awayRank": 99}

                # --- 🔍 離脱者情報の取得（これが当時機能していた本物です） ---
                home_injuries = []
                away_injuries = []
                
                # すべてのdivを走査し、見出しとなるステータスを特定するロジック
                for div in soup.find_all('div'):
                    status_text = div.get_text().strip()
                    if status_text in ["出場微妙", "欠場濃厚", "出場停止"]:
                        parent_box = div.find_parent()
                        if parent_box:
                            # 子要素の中からタグ要素だけを抽出
                            tags = [t for t in parent_box.children if t.name is not None]
                            status_index = -1
                            for s_idx, t in enumerate(tags):
                                if t.get_text().strip() == status_text:
                                    status_index = s_idx
                                    break
                            
                            if status_index != -1:
                                # ステータスインデックスより前にあるli要素をホーム側として処理
                                for t in tags[:status_index]:
                                    for li in t.find_all('li'):
                                        txt = li.get_text().strip()
                                        # ポジション表記のあとの名前を正規表現でキャプチャ
                                        p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                                        if p_match:
                                            name = p_match.group(1).strip()
                                            if name and name != "なし" and name not in home_injuries:
                                                home_injuries.append(name)
                                                
                                # ステータスインデックスより後にあるli要素をアウェイ側として処理
                                for t in tags[status_index+1:]:
                                    for li in t.find_all('li'):
                                        txt = li.get_text().strip()
                                        p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                                        if p_match:
                                            name = p_match.group(1).strip()
                                            if name and name != "なし" and name not in away_injuries:
                                                away_injuries.append(name)

                home_injuries_str = " / ".join(home_injuries) if home_injuries else "なし"
                away_injuries_str = " / ".join(away_injuries) if away_injuries else "なし"
                
                # 詳細な過去成績なども一応パースして構造を維持
                extra_stats = parse_team_performance_matrix(soup)
                h_history = parse_match_history_block(soup, 0)
                a_history = parse_match_history_block(soup, 1)

                # 最終出力用オブジェクトの合成
                combined_data = {
                    **basic_info,
                    "homeInjuries": home_injuries_str,
                    "awayInjuries": away_injuries_str,
                    "homeInjuriesCount": len(home_injuries),
                    "awayInjuriesCount": len(away_injuries),
                    "meta": {
                        "matrix": extra_stats,
                        "home_history_count": len(h_history),
                        "away_history_count": len(a_history)
                    }
                }
                
                final_results.append(combined_data)
                
                # ログへの書き出し
                print(f"🌐 [試合No.{idx}] {combined_data.get('homeTeam')}({combined_data.get('homeRank')}位) vs {combined_data.get('awayTeam')}({combined_data.get('awayRank')}位)")
                print(f"   👉 離脱追記: H {len(home_injuries)}人 ({home_injuries_str}) / A {len(away_injuries)}人 ({away_injuries_str})")
                
            except Exception as e:
                print(f"❌ [致命的エラー] 試合No.{idx} (ID: {m_id}) の解析中に予期せぬ例外が発生。")
                print(f"エラー詳細: {e}")
                raise e
            finally:
                context.close()
                
        browser.close()

    # 既存のdata.jsonへ最終的なマージ結果を上書き
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=4)

    print("✨ 離脱者データの追記・統合がすべて正常に完了しました！")

if __name__ == "__main__":
    main()
