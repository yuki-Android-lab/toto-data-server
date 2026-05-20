import urllib.request
from bs4 import BeautifulSoup
from datetime import datetime

def debug_verification():
    # =================================================================
    # 検証1: Yahoo! toto の対戦カードテーブルの「生の構造」を調べる
    # =================================================================
    print("==================== 【検証1】Yahoo! toto の構造解析 ====================")
    url_toto = "https://toto.yahoo.co.jp/toto/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        req = urllib.request.Request(url_toto, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 最初の1試合分に相当する tr または td のテキストをそのまま抽出してみる
        print("【生データ抽出テスト】最初に見つかるテーブル行（tr）のテキスト:")
        rows = soup.find_all('tr')
        
        match_count = 0
        for i, row in enumerate(rows):
            text = row.text.strip()
            # 空白や改行を整理して、1行のテキストとして見やすくする
            clean_text = " / ".join([t.strip() for t in text.split('\n') if t.strip()])
            
            # totoの対戦カードらしき文字列（チーム名やvsなど）が含まれる行をいくつか抽出
            if any(kwd in clean_text for kwd in ["vs", "J1", "J2", "投票"]):
                print(f" 行番号 {i:02d}: {clean_text}")
                match_count += 1
                if match_count >= 5: # 最初の5件だけ確認できれば構造は特定できます
                    break
                    
        if match_count == 0:
            print("  -> 警告: テーブル行から対戦カードらしきテキストが検出できませんでした。")
            
    except Exception as e:
        print(f"【エラー】Yahoo! toto へのアクセス自体に失敗: {e}")


    # =================================================================
    # 検証2: Jリーグ公式サイトの「URLの応答ステータス」を調べる
    # =================================================================
    print("\n==================== 【検証2】Jリーグ公式URLの応答確認 ====================")
    current_year = datetime.now().year
    
    # 検証するURLのパターン
    url_patterns = {
        f"パターンA（西暦あり）": f"https://www.jleague.jp/standings/{current_year}/j1/",
        f"パターンB（西暦なし）": "https://www.jleague.jp/standings/j1/"
    }
    
    for label, url in url_patterns.items():
        print(f"【アクセス試行】{label}: {url}")
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                final_url = response.geturl()
                status = response.getcode()
                print(f"  -> 結果: 接続成功 (Status: {status})")
                print(f"  -> 最終到達URL: {final_url}")
                
                # 冒頭のタイトルタグだけ確認して、正しいページか検証
                html = response.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                title = soup.find('title')
                print(f"  -> ページタイトル: {title.text.strip() if title else 'なし'}")
                
        except urllib.error.HTTPError as e:
            print(f"  -> エラー発生 (Status {e.code}): {e.reason}")
        except Exception as e:
            print(f"  -> 予期せぬエラー: {e}")
            
    print("===========================================================================")

if __name__ == "__main__":
    debug_verification()
