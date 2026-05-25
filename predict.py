import json
import os

print("4️⃣ [predict.py] 【引き分け確率動的連動・雨天ロジック修正版】計算中...")

if not os.path.exists('data.json'):
    print("❌ data.json が見つかりません！")
    exit(1)

with open('data.json', 'r', encoding='utf-8') as f:
    match_list = json.load(f)

def calculate_probability(home_pt, away_pt, is_rainy=False):
    """
    実力拮抗時や雨天時に、引き分け(0)の確率が35%〜45%超まで
    ダイレクトに跳ね上がる【引き分け本命検知】ロジック
    """
    # 1. 両チームの実力差を算出
    pt_diff = home_pt - away_pt
    abs_diff = abs(pt_diff)
    
    # 2. 【引き分け（0）の超優先・動的計算】
    if abs_diff <= 3:
        # ポイント差がわずか3以内の「完全な互角カード」なら、引き分けベースを38%に設定
        d_pct = 38
    elif abs_diff <= 10:
        # 10以内の競合カードなら32%
        d_pct = 32
    else:
        # 大差のゲームなら、実力決着しやすいので引き分け率をガクッと下げる
        d_pct = max(14, int(30 - (abs_diff * 0.5)))
        
    # 【引き分けブースター要素】
    # 互角（差が5以内）かつ「雨の日」なら、ピッチコンディション悪化によるドロー確率を【+5%】ダイレクト加算！
    if abs_diff <= 5 and is_rainy:
        d_pct += 5

    # 3. 残りの確率をホームとアウェイに素直に分配
    remaining = 100 - d_pct
    total_pt = home_pt + away_pt
    
    h_pure_pct = int(remaining * (home_pt / total_pt))
    a_pure_pct = remaining - h_pure_pct
    
    # 4. 最後の微調整（アウェイからホームへ2%だけ色をつける）
    # 引き分けが主役の時は、この補正で逆転させないように絶妙に調整
    if a_pure_pct > 2:
        h_pct = h_pure_pct + 2
        a_pct = a_pure_pct - 2
    else:
        h_pct = h_pure_pct
        a_pct = a_pure_pct
        
    return h_pct, d_pct, a_pct
    
def judge_forecast(h_pct, d_pct, a_pct):
    """確率から本命と対抗をジャッジする関数（閾値10%で拮抗時は2択化）"""
    pcts = [("1", h_pct), ("0", d_pct), ("2", a_pct)]
    sorted_pcts = sorted(pcts, key=lambda x: x[1], reverse=True)
    
    top1_lbl, top1_val = sorted_pcts[0]
    top2_lbl, top2_val = sorted_pcts[1]
    
    # 最高確率と2番目の差が10%未満の時はマルチ買い（2択）にする
    if (top1_val - top2_val) >= 10:
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
    
    h_goal = int(m.get("homeGoal", 0)) if m.get("homeGoal") is not None else 0
    a_goal = int(m.get("awayGoal", 0)) if m.get("awayGoal") is not None else 0
    h_lose = int(m.get("homeLose", 0)) if m.get("homeLose") is not None else 0
    a_lose = int(m.get("awayLose", 0)) if m.get("awayLose") is not None else 0
    
    h_injuries = m.get("homeInjuries", [])
    a_injuries = m.get("awayInjuries", [])
    h_inj_count = len(h_injuries) if isinstance(h_injuries, list) else 0
    a_inj_count = len(a_injuries) if isinstance(a_injuries, list) else 0
    h_df_inj_count = sum(1 for p in h_injuries if isinstance(p, dict) and p.get("pos") in ["DF", "GK"])
    a_df_inj_count = sum(1 for p in a_injuries if isinstance(p, dict) and p.get("pos") in ["DF", "GK"])

    # ==========================================
    # ☀️ 晴れの日の計算ロジック（ベースを100ptに戻して安定化）
    # ==========================================
    h_pt_sunny = 100
    a_pt_sunny = 100
    
    # ① 順位差ポイント（1順位＝3pt）
    if h_rank < a_rank: h_pt_sunny += (a_rank - h_rank) * 3
    elif a_rank < h_rank: a_pt_sunny += (h_rank - a_rank) * 3
        
    # ② 得失点差補正（純粋な得失点差をそのまま反映）
    h_pt_sunny += (h_goal - h_lose)
    a_pt_sunny += (a_goal - a_lose)
        
    # ③ コンディションポイント
    h_pt_sunny += 20 if h_cond_coef > 0 else (-40 if h_cond_coef < 0 else 0)
    a_pt_sunny += 20 if a_cond_coef > 0 else (-40 if a_cond_coef < 0 else 0)
    
    # ④ 主力級怪我人ペナルティ
    h_pt_sunny -= h_inj_count * 15
    a_pt_sunny -= a_inj_count * 15
    
    # ⑤ 過密日程ペナルティ
    if h_days <= 2: h_pt_sunny -= 10
    if a_days <= 2: a_pt_sunny -= 10
    
    h_pt_sunny = max(10, h_pt_sunny)
    a_pt_sunny = max(10, a_pt_sunny)
    
    h_pct_s, d_pct_s, a_pct_s = calculate_probability(h_pt_sunny, a_pt_sunny)
    forecast_sunny = judge_forecast(h_pct_s, d_pct_s, a_pct_s)

    # ==========================================
    # ☔ 雨の日の計算ロジック（異常なポイント高騰を修正）
    # ==========================================
    h_pt_rainy = 100
    a_pt_rainy = 100
    
    # ① 順位差ポイント（雨の日は影響を「1順位＝1.5pt」に半減）
    if h_rank < a_rank: h_pt_rainy += int((a_rank - h_rank) * 1.5)
    elif a_rank < h_rank: a_pt_rainy += int((h_rank - a_rank) * 1.5)
        
    # ② 得失点補正（雨の日は総得点の影響を無視し、「総失点の少なさ」だけをマイナス加算する）
    h_pt_rainy -= h_lose * 1.5
    a_pt_rainy -= a_lose * 1.5
        
    # ③ コンディションポイント（晴れと同様）
    h_pt_rainy += 20 if h_cond_coef > 0 else (-40 if h_cond_coef < 0 else 0)
    a_pt_rainy += 20 if a_cond_coef > 0 else (-40 if a_cond_coef < 0 else 0)
    
    # ④ 主力級怪我人ペナルティ（雨の日はDF/GKの怪我人ペナルティを2倍重くする）
    h_pt_rainy -= (h_inj_count * 15 + h_df_inj_count * 15)
    a_pt_rainy -= (a_inj_count * 15 + a_df_inj_count * 15)
    
    if h_days <= 2: h_pt_rainy -= 10
    if a_days <= 2: a_pt_rainy -= 10
    
    h_pt_rainy = max(10, h_pt_rainy)
    a_pt_rainy = max(10, a_pt_rainy)
    
    h_pct_r, d_pct_r, a_pct_r = calculate_probability(h_pt_rainy, a_pt_rainy)
    forecast_rainy = judge_forecast(h_pct_r, d_pct_r, a_pct_r)

    # ==========================================
    # 📝 結果出力
    # ==========================================
    print(f"⚽ 試合No.{match_no}: {home_team} vs {away_team}")
    print(f"  ☀️ 晴れpt -> {home_team}: {h_pt_sunny}pt / {away_team}: {a_pt_sunny}pt")
    print(f"     [確率] 🏠勝:{h_pct_s}%  △分:{d_pct_s}%  🚀負:{a_pct_s}%  ➡️  【予想：{forecast_sunny}】")
    print(f"  ☔ 雨天pt -> {home_team}: {h_pt_rainy}pt / {away_team}: {a_pt_rainy}pt")
    print(f"     [確率] 🏠勝:{h_pct_r}%  △分:{d_pct_r}%  🚀負:{a_pct_r}%  ➡️  【予想：{forecast_rainy}】")
    print("-" * 60)

    m["forecastSunny"] = forecast_sunny
    m["forecastSunnyDetails"] = {"homePct": h_pct_s, "drawPct": d_pct_s, "awayPct": a_pct_s, "homePt": h_pt_sunny, "awayPt": a_pt_sunny}
    m["forecastRainy"] = forecast_rainy
    m["forecastRainyDetails"] = {"homePct": h_pct_r, "drawPct": d_pct_r, "awayPct": a_pct_r, "homePt": h_pt_rainy, "awayPt": a_pt_rainy}

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("💾 [predict.py] 引き分け確率の動的連動化、および雨天バグの修正が完了しました！")
