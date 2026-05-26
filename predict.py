import json
import os
import re

print("4️⃣ [predict.py] 【引き分け確率動的連動・調子ロジック修正版】計算中...")

if not os.path.exists('data.json'):
    print("❌ data.json が見つかりません！")
    exit(1)

with open('data.json', 'r', encoding='utf-8') as f:
    match_list = json.load(f)

def calculate_probability(home_pt, away_pt, is_rainy=False):
    """pt差に応じて引き分け確率を動的に変動させるコアロジック"""
    pt_diff = home_pt - away_pt
    abs_diff = abs(pt_diff)
    
    # 1. 【引き分け確率の動的連動】
    if abs_diff <= 1:
        d_pct = 32
    elif abs_diff <= 4:
        d_pct = 26
    else:
        d_pct = max(12, int(22 - (abs_diff * 0.4)))
        
    # 2. ウエイト計算（アウェイカウンター補正）
    weight_h = home_pt + (pt_diff * 0.5)
    weight_a = away_pt - (pt_diff * 0.5)
    
    boost_applied = False
    if abs_diff <= 6:
        weight_a += 8
        boost_applied = True
    
    weight_h = max(10, weight_h)
    weight_a = max(10, weight_a)
    total_weight = weight_h + weight_a
    
    # 3. 確率の分配
    remaining = 100 - d_pct
    h_pct = int(remaining * (weight_h / total_weight))
    a_pct = remaining - h_pct
    
    return h_pct, d_pct, a_pct, {"weight_h": weight_h, "weight_a": weight_a, "boost_applied": boost_applied}
    
def judge_forecast(h_pct, d_pct, a_pct):
    """本命・対抗の判定"""
    pcts = [("1", h_pct), ("0", d_pct), ("2", a_pct)]
    sorted_pcts = sorted(pcts, key=lambda x: x[1], reverse=True)
    if (sorted_pcts[0][1] - sorted_pcts[1][1]) >= 10:
        return sorted_pcts[0][0]
    return f"{sorted_pcts[0][0]}({sorted_pcts[1][0]})"

def extract_days(interval_str):
    """「中5日」などの文字列から数値を抽出"""
    if not interval_str: return 6
    match = re.search(r'\d+', str(interval_str))
    return int(match.group()) if match else 6

# 13試合のループ
for m in match_list:
    match_no = m["matchNo"]
    
    # JSONの生データを確実にパース
    h_rank = int(m.get("homeRank", 10))
    a_rank = int(m.get("awayRank", 10))
    h_days = extract_days(m.get("homeInterval"))
    a_days = extract_days(m.get("awayInterval"))
    
    # 💥【修正】調子係数（例: -0.5 をそのまま計算に使用する）
    h_cond_coef = float(m.get("homeConditionCoef", 0.0))
    a_cond_coef = float(m.get("awayConditionCoef", 0.0))
    
    h_goal = int(m.get("homeGoalsFor", 0))
    h_lose = int(m.get("homeGoalsAgainst", 0))
    a_goal = int(m.get("awayGoalsFor", 0))
    a_lose = int(m.get("awayGoalsAgainst", 0))
    h_inj_count = int(m.get("homeInjuriesCount", 0))
    a_inj_count = int(m.get("awayInjuriesCount", 0))
    
    # --------------------------------------------------------
    # ☀️ 【晴れpt】の再計算
    # --------------------------------------------------------
    h_rank_pt_s = (a_rank - h_rank) * 3 if h_rank < a_rank else 0
    a_rank_pt_s = (h_rank - a_rank) * 3 if a_rank < h_rank else 0
    h_goal_pt_s = (h_goal - h_lose)
    a_goal_pt_s = (a_goal - a_lose)
    
    # 💥【修正】固定値の-40を廃止し、係数に応じた動的ptに（例: -0.5 * 60 = -30pt）
    h_cond_pt_s = int(h_cond_coef * 60)
    a_cond_pt_s = int(a_cond_coef * 60)
    
    h_inj_pt_s = -(h_inj_count * 15)
    a_inj_pt_s = -(a_inj_count * 15)
    h_rest_pt_s = -10 if h_days <= 2 else 0
    a_rest_pt_s = -10 if a_days <= 2 else 0

    h_pt_sunny = max(10, 100 + h_rank_pt_s + h_goal_pt_s + h_cond_pt_s + h_inj_pt_s + h_rest_pt_s)
    a_pt_sunny = max(10, 100 + a_rank_pt_s + a_goal_pt_s + a_cond_pt_s + a_inj_pt_s + a_rest_pt_s)
    
    h_pct_s, d_pct_s, a_pct_s, det_s = calculate_probability(h_pt_sunny, a_pt_sunny, is_rainy=False)
    forecast_sunny = judge_forecast(h_pct_s, d_pct_s, a_pct_s)

    # --------------------------------------------------------
    # ☔ 【雨天pt】の再計算
    # --------------------------------------------------------
    h_rank_pt_r = int((a_rank - h_rank) * 1.5) if h_rank < a_rank else 0
    a_rank_pt_r = int((h_rank - a_rank) * 1.5) if a_rank < h_rank else 0
    h_goal_pt_r = -(h_lose * 1.5)
    a_goal_pt_r = -(a_lose * 1.5)
    
    # 雨天時も同様に動的処理
    h_cond_pt_r = h_cond_pt_s
    a_cond_pt_r = a_cond_pt_s
    
    h_inj_pt_r = -(h_inj_count * 15)
    a_inj_pt_r = -(a_inj_count * 15)
    h_rest_pt_r = h_rest_pt_s
    a_rest_pt_r = a_rest_pt_s

    h_pt_rainy = max(10, 100 + h_rank_pt_r + h_goal_pt_r + h_cond_pt_r + h_inj_pt_r + h_rest_pt_r)
    a_pt_rainy = max(10, 100 + a_rank_pt_r + a_goal_pt_r + a_cond_pt_r + a_inj_pt_r + a_rest_pt_r)
    
    h_pct_r, d_pct_r, a_pct_r, det_r = calculate_probability(h_pt_rainy, a_pt_rainy, is_rainy=True)
    forecast_rainy = judge_forecast(h_pct_r, d_pct_r, a_pct_r)

    # 📝 結果出力
    print(f"⚽ 試合No.{match_no}: {m['homeTeam']} vs {m['awayTeam']}")
    print(f"  ☀️ 【晴れpt の詳細内訳】(初期値 100pt スタート)")
    print(f"    ・①順位差影響 -> 🏠 {h_rank_pt_s:+}pt / 🚀 {a_rank_pt_s:+}pt  (順位: 🏠{h_rank}位 vs 🚀{a_rank}位)")
    print(f"    ・②得失点補正 -> 🏠 {h_goal_pt_s:+}pt / 🚀 {a_goal_pt_s:+}pt  (総得失: 🏠{h_goal}-{h_lose} vs 🚀{a_goal}-{a_lose})")
    print(f"    ・③調子係数   -> 🏠 {h_cond_pt_s:+}pt / 🚀 {a_cond_pt_s:+}pt  (係数: 🏠{h_cond_coef} vs 🚀{a_cond_coef})")
    print(f"    ・④怪我人ペナ -> 🏠 {h_inj_pt_s:+}pt / 🚀 {a_inj_pt_s:+}pt  (人数: 🏠{h_inj_count}人 vs 🚀{a_inj_count}人)")
    print(f"    ・⑤過密日程   -> 🏠 {h_rest_pt_s:+}pt / 🚀 {a_rest_pt_s:+}pt  (間隔: 🏠{h_days}日 vs 🚀{a_days}日)")
    print(f"    ⇒ 最終総合pt  -> 🏠 {h_pt_sunny}pt vs 🚀 {a_pt_sunny}pt")
    print(f"    ・変換ウエイト -> 🏠 {det_s['weight_h']:.1f} vs 🚀 {det_s['weight_a']:.1f} " + ("🔥(J2アウェイ・カウンター適用)" if det_s['boost_applied'] else ""))
    print(f"    [確率] 🏠勝:{h_pct_s}%  △分:{d_pct_s}%  🚀負:{a_pct_s}%  ➡️  【予想：{forecast_sunny}】")
    print(f"  --------------------------------------------------")
    print(f"  ☔ 【雨天pt の詳細内訳】")
    print(f"    ・③調子係数   -> 🏠 {h_cond_pt_r:+}pt / 🚀 {a_cond_pt_r:+}pt")
    print(f"    ⇒ 最終総合pt  -> 🏠 {h_pt_rainy:.1f}pt vs 🚀 {a_pt_rainy:.1f}pt")
    print(f"    [確率] 🏠勝:{h_pct_r}%  △分:{d_pct_r}%  🚀負:{a_pct_r}%  ➡️  【予想：{forecast_rainy}】")
    print("-" * 60)

    # JSON上書き
    m["forecastSunny"] = forecast_sunny
    m["forecastSunnyDetails"] = {"homePct": h_pct_s, "drawPct": d_pct_s, "awayPct": a_pct_s, "homePt": h_pt_sunny, "awayPt": a_pt_sunny}
    m["forecastRainy"] = forecast_rainy
    m["forecastRainyDetails"] = {"homePct": h_pct_r, "drawPct": d_pct_r, "awayPct": a_pct_r, "homePt": h_pt_rainy, "awayPt": a_pt_rainy}

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("💾 [predict.py] 調子係数の動的乗算化が完了しました。")
