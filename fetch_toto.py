import urllib.request
import sys

def main():
    url = "https://toto.yahoo.co.jp/toto/?holdId=1631"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print("==================================================")
    print(f"【検証要求】URL: {url} からの生HTMLをダンプします")
    print("==================================================\n")
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        # 取得したHTMLをそのまま標準出力にすべて書き出します
        print(html)
        
        print("\n==================================================")
        print("【検証要求】HTMLのダンプが正常に終了しました")
        print("==================================================")
        
    except Exception as e:
        print(f"\n【エラー】HTMLの取得自体に失敗しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
