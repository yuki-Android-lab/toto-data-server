import urllib.request
import re

def inspect_toto_html():
    print("==================== 【事実確認】Yahoo! toto 生テキスト抽出 ====================")
    url = "https://toto.yahoo.co.jp/toto/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        # 1. ページ全体に「福岡」や「神戸」といった文字がそもそも含まれているか確認
        # (これでアクセスしているURLが正しいかどうかが100%分かります)
        has_fukuoka = "福岡" in html
        has_kobe = "神戸" in html
        print(f"■ キーワードチェック: 『福岡』の存在={has_fukuoka} / 『神戸』の存在={has_kobe}")
        
        # 2. HTMLが長すぎるため、aタグやdivタグなど、テキストを含んでいる主要な行を30行だけ抽出
        print("\n■ HTML内のテキストエリア周辺の構造（抜粋）:")
        lines = html.split('\n')
        printed_count = 0
        
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
                
            # チーム名が入りそうな箇所（<a>タグ、<td>タグ、あるいはクラス指定がある行）を絞り込む
            if any(kwd in line_str for kwd in ["<a", "<td", "class=", "team", "match"]):
                # タグを極力見やすくするために、前後の文字も含めて出力
                print(f"  行データ: {line_str[:120]}")
                printed_count += 1
                if printed_count >= 40: # 40行見れば、どういう規則でチーム名が並んでいるか必ず特定できます
                    break
                    
    except Exception as e:
        print(f"【通信エラー】アクセス自体に失敗しています: {e}")
    print("==========================================================================")

if __name__ == "__main__":
    inspect_toto_html()
