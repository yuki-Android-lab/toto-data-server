import json
import re
import os
import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# ==============================================================================
# 1. ユーティリティ関数群
# ==============================================================================
def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()

def extract_number(text: str) -> int:
    match = re.search(r'\d+', text)
    return int(match.group()) if match else 0

# ==============================================================================
# 2. 基本情報（チーム名・順位）パース関数
#    ※ 当時、ここでペア抽出に失敗して ValueError を吐いて強制終了していた部分です
# ==============================================================================
def parse_basic_info(soup: BeautifulSoup, hold_id: int, match_no: int) -> dict:
    try:
        # 当時のスクリプトがチーム名や順位を探そうとしていた古いセレクタロジック
        # (Next.js化により構造が変わり、ここが None や空になっていました)
        teams = soup.find_all('div', class_='team-name')
        ranks = soup.find_all('span', class_='rank-number')
        
        # 厳格なバリデーションチェック（ここで落ちて強制終了していました）
        if not teams or len(teams) < 2:
            raise ValueError(f"❌ [試合No.{match_no}] チーム名または順位のペア抽出に完全に失敗しました。スクリプトを強制終了します。")
            
        home_team = normalize_text(teams[0].get_text())
        away_team = normalize_text(teams[1].get_text())
        
        home_rank = extract_number(ranks[0].get_text()) if len(ranks) > 0 else 99
        away_rank = extract_number(ranks[1].get_text()) if len(ranks) > 1 else 99
        
        return {
            "holdId": hold_id,
            "matchNo": match_no,
            "homeTeam": home_team,
            "awayTeam": away_team,
            "homeRank": home_rank,
            "awayRank": away_rank
        }
    except Exception as e:
        # 当時画像にあったエラーハンドリングと全く同じメッセージを発生させます
        raise ValueError(f"❌ [試合No.{match_no}] チーム名または順位のペア抽出に完全に失敗しました。スクリプトを強制終了します。")

# ==============================================================================
# 3. 過去スタッツ・対戦成績等のパース関数（ステップ数を肥大化させていた要因）
# ==============================================================================
def parse_extra_stats(soup: BeautifulSoup) -> dict:
    stats = {"home_form": [], "away_form": []}
    # 昔のサイトのテーブル構造を解析するロジック（現在は不発）
    tables = soup.find_all('table', class_='stats-table')
    for idx, table in enumerate(tables):
        rows = table.find_all('tr')
        for row in rows[1:]:
            cols = row.find_all('td')
            if len(cols) >= 3:
                result = normalize_text(cols[1].get_text())
                if idx == 0:
                    stats["home_form"].append(result)
                else:
                    stats["away_form"].append(result)
    return stats

# ==============================================================================
# 4. メイン処理
# ==============================================================================
def main():
    hold_id = 1512
    # 13試合分のID定義
    match_ids = [27736, 27737, 27738, 27739, 27740, 27741, 27742, 27743, 27744, 27745, 27746, 27747, 27748]
    
    print(f"🔄 開催回 ID: {hold_id} の全13試合に対して 『完全独立ペア抽出』 を実行します...")
    
    if not os.path.exists('data.json'):
        # ファイルがない場合は新規に器を作成
        match_list = []
        for idx, m_id in enumerate(match_ids, start=1):
            match_list.append({"matchNo": idx, "holdId": hold_id})
    else:
        with open('data.json', 'r', encoding='utf-8') as f:
            match_list = json.load(f)

    results = []

    with sync_playwright() as p:
        # ヘッドレスモードでブラウザ起動
        browser = p.chromium.launch(headless=True)
        
        for idx, match_id in enumerate(match_ids, start=1):
            target_url = f"https://www.totoone.jp/match/{match_id}"
            print(f"✈️ [試合No.{idx}] 解析中: {target_url}")
            
            context = browser.new_context(
                viewport={"width": 1280, "height": 1024},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            try:
                # 当時の設定：DOMコンテンツロード時点で即座にHTMLを取得する
                page.goto(target_url, wait_until="domcontentloaded")
                html = page.content()
                
                # lxmlパーサーを使用してスープを作成（ここでlxmlがないと Actions が落ちていました）
                try:
                    soup = BeautifulSoup(html, "lxml")
                except Exception:
                    # 保険としてhtml.parser
                    soup = BeautifulSoup(html, "html.parser")
                
                # --- ① 基本情報の抽出 ---
                # 当時はここで「怪我人は取れているのに、チーム名取得で例外を吐いて全体の処理が即死」していました。
                # 検証用に、既存の data.json にデータがある場合はそれを活かし、なければパースを試みます。
                try:
                    basic_info = parse_basic_info(soup, hold_id, idx)
                except ValueError as ve:
                    # 既存のdata.jsonにチーム名が既に入っているなら、延命して処理を続行させるコード
                    #（ただし、ここのsoupからはチーム名が抜けない状態です）
                    found_existing = False
                    for existing_data in match_list:
                        if existing_data.get("matchNo") == idx and "homeTeam" in existing_data:
                            basic_info = existing_data
                            found_existing = True
                            break
                    if not found_existing:
                        print(f"❌ [致命的エラー] 試合No.{idx} (ID: {match_id}) のデータが正しくパースできませんでした。")
                        print(f"エラー内容: {ve}")
                        print("データの信憑性が担保できないため、ワークフローをエラーとして強制終了します。")
                        sys.exit(1)

                # --- ② 離脱者情報の抽出（当時のロジックそのまま） ---
                home_injuries = []
                away_injuries = []
                
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
                                # ホーム側の走査
                                for t in tags[:status_index]:
                                    for li in t.find_all('li'):
                                        txt = li.get_text().strip()
                                        p_match = re.search(r"(?:GK|DF|MF|FW)\s*([^\s（(]+)", txt)
                                        if p_match:
                                            name = p_match.group(1).strip()
                                            if name and name != "なし" and name not in home_injuries:
                                                home_injuries.append(name)
                                                
                                # アウェイ側の走査
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
                
                # 最終データのマージ
                full_match_data = {
                    **basic_info,
                    "homeInjuries": home_injuries_str,
                    "awayInjuries": away_injuries_str,
                    "homeInjuriesCount": len(home_injuries),
                    "awayInjuriesCount": len(away_injuries)
                }
                
                results.append(full_match_data)
                
                print(f"🌐 [試合No.{idx}] {full_match_data.get('homeTeam')}({full_match_data.get('homeRank')}位) vs {full_match_data.get('awayTeam')}({full_match_data.get('awayRank')}位)")
                print(f"   👉 離脱追記: H {len(home_injuries)}人 ({home_injuries_str}) / A {len(away_injuries)}人 ({away_injuries_str})")
                
            except Exception as e:
                print(f"❌ [致命的エラー] 試合No.{idx} (ID: {match_id}) のデータが正しくパースできませんでした。")
                print(f"エラー内容: {e}")
                print("データの信憑性が担保できないため、ワークフローをエラーとして強制終了します。")
                raise e
            finally:
                context.close()
                
        browser.close()

    # マージした結果をdata.jsonに保存
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("✨ 離脱者データの追記・統合がすべて正常に完了しました！")

if __name__ == "__main__":
    main()
