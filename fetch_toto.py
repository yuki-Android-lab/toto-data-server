import urllib.request
from bs4 import BeautifulSoup
import re

def check_yahoo_j1():
    url = "https://soccer.yahoo.co.jp/jleague/category/j1ss/standings"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    print("=== [DEBUG] 1. Yahoo J1ss ページの生データをチェックします ===")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # そもそもtrタグが何個あるか
        all_trs = soup.find_all('tr')
        print(f"  -> ページ内の全 <tr> タグの数: {len(all_trs)} 個")
        
        # 上位5件のテキストをそのまま出してみる
        print("\n=== [DEBUG] 2. 検出された tr 内のテキスト（先頭5件） ===")
        count = 0
        for row in all_trs:
            cols = row.find_all(['td', 'th'])
            col_texts = [c.text.strip().replace("\n", "") for c in cols]
            if col_texts:
                print(f"    行[{count}]: {col_texts[:3]}")  # 順位、チーム名あたりを出力
                count += 1
            if count >= 5:
                break
                
    except Exception as e:
        print(f"  ❌ エラー発生: {e}")

if __name__ == "__main__":
    check_yahoo_j1()
