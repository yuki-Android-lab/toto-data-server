import json
import os

print("📊 [predict_pattern.py] 【多次元出目パターン解析 ❌ 現実データ融合版】")

# --------------------------------------------------------
# 💾 ご提示いただいた過去20回分の出目データ（歯抜けを詰めた20回分）
# --------------------------------------------------------
PAST_RESULTS = [
    ["2", "2", "1", "2", "1", "1", "2", "2", "1", "1", "2", "0", "2"],  # 1604
    ["1", "2", "2", "2", "1", "2", "1", "2", "0", "1", "0", "1", "1"],  # 1605
    ["0", "2", "1", "0", "1", "2", "1", "1", "1", "0", "0", "0", "2"],  # 1606
    ["2", "0", "0", "0", "1", "1", "1", "2", "1", "2", "2", "2", "0"],  # 1608
    ["0", "0", "1", "2", "2", "0", "0", "0", "0", "1", "1", "2", "2"],  # 1609
    ["2", "1", "1", "2", "2", "2", "2", "0", "1", "0", "1", "2", "0"],  # 1610
    ["1", "0", "1", "0", "0", "2", "2", "0", "2", "2", "2", "2", "0"],  # 1613
    ["1", "1", "2", "1", "1", "1", "1", "0", "0", "0", "0", "2", "0"],  # 1614
    ["1", "2", "0", "2", "1", "2", "0", "1", "1", "1", "2", "1", "2"],  # 1616
    ["2", "1", "0", "2", "1", "0", "1", "0", "2", "0", "1", "1", "1"],  # 1618
    ["2", "1", "0", "0", "1", "0", "2", "1", "2", "1", "1", "0", "0"],  # 1619
    ["1", "1", "2", "2", "1", "0", "1", "2", "1", "0", "2", "2", "1"],  # 1620
    ["0", "0", "1", "1", "2", "1", "2", "0", "2", "1", "2", "1", "1"],  # 1621
    ["2", "1", "1", "0", "0", "1", "1", "1", "1", "2", "2", "1", "2"],  # 1622
    ["1", "2", "1", "2", "1", "0", "1", "0", "0", "2", "2", "1", "1"],  # 1624
    ["2", "0", "0", "1", "2", "1", "0", "0", "0", "2", "1", "1", "1"],  # 1625
    ["1", "1", "2", "1", "1", "0", "1", "0", "2", "0", "2", "0", "0"],  # 1626
    ["0", "0", "2", "0", "1", "1", "1", "1", "2", "1", "2", "1", "2"],  # 1627
    ["2", "0", "2", "2", "1", "1", "0", "1", "2", "1", "1", "2", "2"],  # 1628
    ["2", "2", "0", "2", "2", "0", "1", "1", "0", "2", "0", "2", "2"],  # 1630 (直近)
]

# --------------------------------------------------------
# 🧠 ④ 出目パターン解析エンジン（横・縦・ブロック）
# --------------------------------------------------------
def analyze_pattern_forecast():
    """過去20回から、1〜13試合の次に来そうな出目を多次元予測する"""
    forecast_iv = []
    
    # ブロックの定義 (0-indexed)
    blocks = [
        {"name": "第1ブロック(No1-3)",  "range": range(0, 3)},
        {"name": "第2ブロック(No4-6)",  "range": range(3, 6)},
        {"name": "第3ブロック(No7-9)",  "range": range(6, 9)},
        {"name": "第4ブロック(No10-13)", "range": range(9, 13)}
    ]

    # 全体の縦の出目総数（過去20回での1開催あたりの平均出現数）
    total_counts = {"1": 0, "0": 0, "2": 0}
    for row in PAST_RESULTS:
        for val in row:
            total_counts[val] += 1
            
    for m_idx in range(13):  # 試合1〜13
        # 1️⃣ 横の解析：対象試合Noの過去20回の流れ
        history = [row[m_idx] for row in PAST_RESULTS]
        last_3 = history[-3:]  # 直近3回
        
        # 基本的な流れのスコアリング（過去20回中でのその出目の出現確率）
        score_1 = history.count("1") / 20.0
        score_0 = history.count("0") / 20.0
        score_2 = history.count("2") / 20.0
        
        # 直近の連続性（横のパターンマッチング）
        if last_3 == ["1", "1", "1"]: score_1 += 0.5  # 1連発
        elif last_3 == ["0", "1", "2"]: score_0 += 0.5  # 循環
        elif last_3 == ["1", "2", "0"]: score_1 += 0.5  # 循環
        elif last_3 == ["2", "2", "0"]: score_0 += 0.5  # リピート後変化
        elif last_3 == ["2", "1", "1"]: score_1 += 0.3; score_2 += 0.3  # マルチ候補
        elif last_3 == ["1", "1", "0"]: score_0 += 0.3; score_1 += 0.3  # マルチ候補
        
        # 2️⃣ ブロックの解析
        # 自分がどのブロックに属しているか探し、そのブロックでの過去20回の出目偏りを加算
        for b in blocks:
            if m_idx in b["range"]:
                b_history = []
                for row in PAST_RESULTS:
                    for idx in b["range"]:
                        b_history.append(row[idx])
                b_total = len(b_history)
                score_1 += (b_history.count("1") / b_total) * 0.2
                score_0 += (b_history.count("0") / b_total) * 0.2
                score_2 += (b_history.count("2") / b_total) * 0.2

        # スコアの最も高いものを出目予想とする
        scores = [("1", score_1), ("0", score_0), ("2", score_2)]
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 特殊なマルチ条件（上位2つの差が極めて僅差ならダブルにする）
        if abs(scores[0][1] - scores[1][1]) < 0.05:
            forecast_iv.append(f"{scores[0][0]},{scores[1][0]}")
        else:
            forecast_iv.append(scores[0][0])
            
    return forecast_iv

# --------------------------------------------------------
# 🤝 ⑤ 融合シールド判定ロジック
# --------------------------------------------------------
def judge_fusion(forecast_reality, forecast_pattern):
    """①〜③の現実予想と、④のパターン予想をぶつけて最終結論を出す"""
    # パターン側が「1,2」などのダブル予想だった場合の処理
    p_elements = forecast_pattern.split(",")
    
    # 1. 一致パターン
    if forecast_reality in p_elements:
        return forecast_reality
        
    # 2. 不一致（カウンター）パターン：お互いがシングルで食い違った場合、第3の選択肢を狙う
    if len(p_elements) == 1:
        all_options = {"1", "0", "2"}
        used_options = {forecast_reality, forecast_pattern}
        leftover = all_options - used_options
        if leftover:
            return list(leftover)[0]  # 残った最後の1つ（大穴・波乱裏目）を返す
            
    # パターン側がダブルで現実がそこから外れた場合は、現実側を優先（保険）
    return forecast_reality

# --------------------------------------------------------
# 🚀 メイン処理
# --------------------------------------------------------
if not os.path.exists('data.json'):
    print("❌ data.json（現実データ）が見つかりません。")
    exit(1)

with open('data.json', 'r', encoding='utf-8') as f:
    match_list = json.load(f)

# ④ の多次元出目パターン予想を一括計算
pattern_predictions = analyze_pattern_forecast()

print(f"\n====================== 🎯 最終クロス融合判定一覧 ======================")

for m in match_list:
    match_no = m["matchNo"]
    m_idx = match_no - 1  # 0から始まるインデックス
    
    # --- ①〜③ 現実ベースの簡易判定（前回のロジック流用またはシンプルな晴れ予想） ---
    # ※ここでは既存のforecastSunnyの文字列（"1", "0", "2"など）をベースの「現実予想」として抽出します。
    # もしカッコ付き（例: "1(0)"）なら、本命の先頭1文字を採用
    raw_sunny = m.get("forecastSunny", "1")
    forecast_reality = raw_sunny[0] 
    
    # ④ 出目パターン側の予想を取得
    forecast_pattern = pattern_predictions[m_idx]
    
    # ⑤ 融合シールドの発動
    final_forecast = judge_fusion(forecast_reality, forecast_pattern)
    
    # 画面に根拠をすべて並べて出力
    print(f"⚽ 試合No.{match_no:02d}: {m['homeTeam']} vs {m['awayTeam']}")
    print(f"  └ 🛠️ ①〜③ [現実データ本命] ： 【 {forecast_reality} 】")
    print(f"  └ 🎲 ④   [出目20回多次元] ： 【 {forecast_pattern} 】")
    
    if forecast_reality == forecast_pattern:
        print(f"  ➡️ 🔥 ⑤ [完全一致] 軸確定馬券！最終予想 ➡️➡️ 【 {final_forecast} 】")
    elif "," in forecast_pattern and forecast_reality in forecast_pattern.split(","):
        print(f"  ➡️ 📈 ⑤ [パターン内合致] 最終予想 ➡️➡️ 【 {final_forecast} 】")
    else:
        print(f"  ➡️ ⚡ ⑤ [不一致カウンター発動] 第3の選択肢を突く！ 最終予想 ➡️➡️ 【 \033[31m{final_forecast}\033[0m 】")
    print("-" * 70)

    # JSONへ新しいアプローチの結果を書き込み
    m["forecastPatternOnly"] = forecast_pattern  # 出目だけの予測
    m["forecastFinalFusion"] = final_forecast    # クロス融合した最終結論

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("\n💾 [predict_pattern.py] 出目パターン解析と融合データの保存が完了しました。")
