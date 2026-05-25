import json
import os

print("4️⃣ [predict.py] 晴れ・雨それぞれの天候予測を計算中（引き分け確率を正常化）...")

# 1. 既存の data.json を読み込む
if not os.path.exists('data.json'):
    print("❌ data.json が見つかりません！")
    exit(1)

with open('data.json', 'r', encoding='utf-8') as f:
    match_list = json.load(f)

def calculate_probability(home_pt, away_pt):
    """
    ポイント比率を素直に反映し、極端なホーム偏りを修正した関数
    """
    total_pt = home_pt + away_pt
    
    # 1. まず引き分け（0）の確率を全体の「28%」としてどっしり固定
    d_pct = 28
    
    # 2. 残りの「72%」を、ホームとアウェイの純粋なポイント比率で分配
    remaining = 100 - d_pct  # 72
    h_pure_pct = int(remaining * (home_pt / total_pt))
    a_pure_pct = remaining - h_pure_pct
    
    # 3. 最後に「ホームアドバンテージ」としてアウェイからホームへ【3%】だけ確率を移す
    # (実力差が僅差のときだけホームが少し有利になり、実力差が大きいときは逆転しない絶妙な塩梅)
    if a_pure_pct > 3:
        h_pct = h_pure_pct + 3
        a_pct = a_pure_pct - 3
    else:
        h_pct = h_pure_pct
        a_pct = a_pure_pct
        
    return h_pct, d_pct, a_pct

def judge_forecast(h_pct, d_pct, a_pct):
    """確率から本命と対抗をジャッジする関数"""
    pcts = [("1", h_pct), ("0", d_pct), ("2", a_pct)]
    # 確率の高い順にソート
    sorted_pcts = sorted(pcts, key=lambda x: x[1], reverse=True)
    
    top1_lbl, top1_val = sorted_pcts[0]
    top2_lbl, top2_val = sorted_pcts[1]
    
    # 【本命・対抗の判定閾値】
    # 1位と2位の確率差が 15% 以上開いていれば本命の一択（自信あり）
    # 差が 15% 未満の僅差であれば、本命（対抗）の2択にする
    if (top1_val - top2_val) >= 15:
        return top1_lbl
    else:
        return f"{top1_lbl}({top2_lbl})"

# 2. 13試合の予測ループ
for m in match_list:
    match_no = m["matchNo"]
    home_team = m["homeTeam"]
    away_team = m["awayTeam"]
    
    h_rank = int(m.get("homeRank", 10)) if m.get("homeRank") is not None else 10
    a_rank = int(m.get("awayRank", 10)) if m.get("awayRank") is not None else 10
    h_days = int(m.get("homeRestDays", 6)) if m.get("homeRestDays") is not None else 6
    a_days = int(m.get("awayRestDays", 6)) if m.get("awayRestDays") is not None else 6
    h_cond_coef = float(m.get("homeConditionCoef", 0.0))
    a_cond_coef = float(m.get("awayConditionCoef", 0.0))
    
    h_injuries = m.get("homeInjuries", [])
    a_injuries = m.get("awayInjuries", [])
    h_inj_count = len(h_injuries) if isinstance(h_injuries, list) else 0
    a_inj_count = len(a_injuries) if isinstance(a_injuries, list) else 0
    h_df_inj_count = sum(1 for p in h_injuries if isinstance(p, dict) and p.get("pos") in ["DF", "GK"])
    a_df_inj_count = sum(1 for p in a_injuries if isinstance(p, dict) and p.get("pos") in ["DF", "GK"])

    # ==========================================
    # ☀️ 晴れの日の計算ロジック
    # ==========================================
    h_pt_sunny = 100
    a_pt_sunny = 100
    
    if h_rank < a_rank:
        h_pt_sunny += (a_rank - h_rank) * 2
    elif a_rank < h_rank:
        a_pt_sunny += (h_rank - a_rank) * 2
        
    h_pt_sunny += 20 if h_cond_coef > 0 else (-50 if h_cond_coef < 0 else 0)
    a_pt_sunny += 20 if a_cond_coef > 0 else (-50 if a_cond_coef < 0 else 0)
    
    h_pt_sunny -= h_inj_count * 15
    a_pt_sunny -= a_inj_count * 15
    
    if h_days <= 2: h_pt_sunny -= 10
    if a_days <= 2: a_pt_sunny -= 10
    
    h_pt_sunny = max(10, h_pt_sunny)
    a_pt_sunny = max(10, a_pt_sunny)
    
    h_pct_s, d_pct_s, a_pct_s = calculate_probability(h_pt_sunny, a_pt_sunny)
    forecast_sunny = judge_forecast(h_pct_s, d_pct_s, a_pct_s)

    # ==========================================
    # ☔ 雨の日の計算ロジック
    # ==========================================
    h_pt_rainy = 100
    a_pt_rainy = 100
    
    if h_rank < a_rank:
        h_pt_rainy += (a_rank - h_rank) * 1
    elif a_rank < h_rank:
        a_pt_rainy += (h_rank - a_rank) * 1
        
    h_pt_rainy += 20 if h_cond_coef > 0 else (-50 if h_cond_coef < 0 else 0)
    a_pt_rainy += 20 if a_cond_coef > 0 else (-50 if a_cond_coef < 0 else 0)
    
    h_pt_rainy -= h_inj_count * 15
    a_pt_rainy -= a_inj_count * 15
    h_pt_rainy -= h_df_inj_count * 15
    a_pt_rainy -= a_df_inj_count * 15
    
    if h_days <= 2: h_pt_rainy -= 10
    if a_days <= 2: a_pt_rainy -= 10
    
    h_pt_rainy = max(10, h_pt_rainy)
    a_pt_rainy = max(10, a_pt_rainy)
    
    h_pct_r, d_pct_r, a_pct_r = calculate_probability(h_pt_rainy, a_pt_rainy)
    forecast_rainy = judge_forecast(h_pct_r, d_pct_r, a_pct_r)

    # ==========================================
    # 📝 画面（ログ）への結果出力
    # ==========================================
    print(f"⚽ 試合No.{match_no}: {home_team} vs {away_team}")
    print(f"  ☀️ 晴れ計算値 -> {home_team}: {h_pt_sunny}pt / {away_team}: {a_pt_sunny}pt")
    print(f"     [確率] 🏠勝:{h_pct_s}%  △分:{d_pct_s}%  🚀負:{a_pct_s}%  ➡️  【予想：{forecast_sunny}】")
    print(f"  ☔ 雨天計算値 -> {home_team}: {h_pt_rainy}pt / {away_team}: {a_pt_rainy}pt")
    print(f"     [確率] 🏠勝:{h_pct_r}%  △分:{d_pct_r}%  🚀負:{a_pct_r}%  ➡️  【予想：{forecast_rainy}】")
    print("-" * 60)

    m["forecastSunny"] = forecast_sunny
    m["forecastSunnyDetails"] = {"homePct": h_pct_s, "drawPct": d_pct_s, "awayPct": a_pct_s, "homePt": h_pt_sunny, "awayPt": a_pt_sunny}
    m["forecastRainy"] = forecast_rainy
    m["forecastRainyDetails"] = {"homePct": h_pct_r, "drawPct": d_pct_r, "awayPct": a_pct_r, "homePt": h_pt_rainy, "awayPt": a_pt_rainy}

# 4. 最終保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("💾 [predict.py] 引き分け確率を正常化し、予測データを data.json に再保存しました！")
