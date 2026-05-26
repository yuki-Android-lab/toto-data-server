import json
import os
import re

print("4️⃣ [predict.py] 【直近調子・文字列ダイレクト判定版】計算中...")

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

def convert_recent_to_pt(recent_str):
    """
    💥【最重要修正】
    一律-0.5になっているCoef数値は無視し、Recentの文字列から直接ptを生成する
    """
    if not recent_str:
        return 0
    
    # 文字列に含まれるキーワードで判定
    if "好調" in recent_str or "絶好調" in recent_str:
        return 20
    elif "普通" in recent_str:
        return 0
    elif "悪化" in recent_str or "不調" in recent_str:
        return -30
    
    return 0  # 判別できない場合はデフォルト0

# 13試合のループ
for m in match_list:
    match_no = m["matchNo"]
    
    # JSONの生データをパース
    h_rank = int(m.get("homeRank", 10))
    a_rank = int(m.get("awayRank", 10))
    h_days = extract_days(m.get("homeInterval"))
    a_days = extract_days(m.get("awayInterval"))
    
    # 💥【修正】文字列（"普通" など）を取得し、関数でptに直接変換
    h_recent_str = m.get("homeRecent", "普通")
    a_recent_str = m.get("awayRecent", "普通")
    h_cond_pt_s = convert_recent_to_pt(h_recent_str)
    a_cond_pt_s = convert_recent_to_pt(a_recent_str)
    
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
    print(f"  ☀️ 【晴れpt の詳細内訳】")
    print(f"    ・③調子係数   -> 🏠 {h_cond_pt_s:+}pt / 🚀 {a_cond_pt_s:+}pt  (直近状態: 🏠{h_recent_str} / 🚀{a_recent_str})")
    print(f"    ⇒ 最終総合pt  -> 🏠 {h_pt_sunny}pt vs 🚀 {a_pt_sunny}pt")
    print(f"    [確率] 🏠勝:{h_pct_s}%  △分:{d_pct_s}%  🚀負:{a_pct_s}%  ➡️  【予想：{forecast_sunny}】")
    print("-" * 60)

    # JSON上書き用の新しい係数を逆算して保存（もし必要なら）
    m["homeConditionCoef"] = float(h_cond_pt_s / 60.0)
    m["awayConditionCoef"] = float(a_cond_pt_s / 60.0)

    m["forecastSunny"] = forecast_sunny
    m["forecastSunnyDetails"] = {"homePct": h_pct_s, "drawPct": d_pct_s, "awayPct": a_pct_s, "homePt": h_pt_sunny, "awayPt": a_pt_sunny}
    m["forecastRainy"] = forecast_rainy
    m["forecastRainyDetails"] = {"homePct": h_pct_r, "drawPct": d_pct_r, "awayPct": a_pct_r, "homePt": h_pt_rainy, "awayPt": a_pt_rainy}

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("💾 [predict.py] 直近調子のテキスト判定への切り替えが完了しました。")
