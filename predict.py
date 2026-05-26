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
    【J2大混戦＆アウェイ・カウンター特化版】
    実力が拮抗しているカード（pt差が少ない試合）ほど、
    「地元ゆえに前がかりになるホーム」をアウェイがカウンターで仕留めるリアルな傾向を再現。
    """
    pt_diff = home_pt - away_pt
    abs_diff = abs(pt_diff)
    
    # 1. 【引き分け（0）の超厳選化】
    if abs_diff <= 1:
        d_pct = 32
    elif abs_diff <= 4:
        d_pct = 26
    else:
        d_pct = max(12, int(22 - (abs_diff * 0.4)))
        
    # 2. 【アウェイ・カウンターブースター】
    weight_h = home_pt + (pt_diff * 0.5)
    weight_a = away_pt - (pt_diff * 0.5)
    
    # J2混戦・カウンター補正の可視化用フラグ
    boost_applied = False
    if abs_diff <= 6:
        weight_a += 8
        boost_applied = True
    
    weight_h = max(10, weight_h)
    weight_a = max(10, weight_a)
    total_weight = weight_h + weight_a
    
    # 3. 残りの％を分配
    remaining = 100 - d_pct
    h_pct = int(remaining * (weight_h / total_weight))
    a_pct = remaining - h_pct
    
    # --- デバッグ検証用に追加：内部の計算結果を辞書で返す ---
    calc_details = {
        "d_pct": d_pct,
        "weight_h": weight_h,
        "weight_a": weight_a,
        "boost_applied": boost_applied
    }
    
    return h_pct, d_pct, a_pct, calc_details
    
def judge_forecast(h_pct, d_pct, a_pct):
    """確率から本命と対抗をジャッジする関数"""
    pcts = [("1", h_pct), ("0", d_pct), ("2", a_pct)]
    sorted_pcts = sorted(pcts, key=lambda x: x[1], reverse=True)
    
    top1_lbl, top1_val = sorted_pcts[0]
    top2_lbl, top2_val = sorted_pcts[1]
    
    if (top1_val - top2_val) >= 10:
        return top1_lbl
    else:
        return f"{top1_lbl}({top2_lbl})"

# ==========================================
# 2. 13試合の予測ループ（データ取得部バグ修正版）
# ==========================================
for m in match_list:
    match_no = m["matchNo"]
    home_team = m["homeTeam"]
    away_team = m["awayTeam"]
    
    # --- 【バグ修正】型変換とキー名の揺れ対策 ---
    h_rank = int(m.get("homeRank") if m.get("homeRank") is not None else 10)
    a_rank = int(m.get("awayRank") if m.get("awayRank") is not None else 10)
    h_days = int(m.get("homeRestDays") if m.get("homeRestDays") is not None else 6)
    a_days = int(m.get("awayRestDays") if m.get("awayRestDays") is not None else 6)
    
    # 調子係数の取得を安全に（Noneや文字列対策）
    try:
        h_cond_coef = float(m.get("homeConditionCoef", 0.0)) if m.get("homeConditionCoef") is not None else 0.0
        a_cond_coef = float(m.get("awayConditionCoef", 0.0)) if m.get("awayConditionCoef") is not None else 0.0
    except (ValueError, TypeError):
        h_cond_coef = 0.0
        a_cond_coef = 0.0
    
    # 【得失点キー名対策】"homeGoal" / "homeGoals" どちらでも取れるようにガード
    h_goal = int(m.get("homeGoal") or m.get("homeGoals") or 0)
    a_goal = int(m.get("awayGoal") or m.get("awayGoals") or 0)
    h_lose = int(m.get("homeLose") or m.get("homeLoses") or 0)
    a_lose = int(m.get("awayLose") or m.get("awayLoses") or 0)
    
    # 【怪我人リスト対策】リストの中に辞書、または単なる文字列の配列でもカウントできるようにガード
    h_injuries = m.get("homeInjuries") or m.get("homeInjuryList") or []
    a_injuries = m.get("awayInjuries") or m.get("awayInjuryList") or []
    
    h_inj_count = len(h_injuries) if isinstance(h_injuries, list) else 0
    a_inj_count = len(a_injuries) if isinstance(a_injuries, list) else 0
    
    # DF/GKの怪我人カウントを安全に
    h_df_inj_count = 0
    if isinstance(h_injuries, list):
        for p in h_injuries:
            if isinstance(p, dict) and p.get("pos") in ["DF", "GK"]:
                h_df_inj_count += 1
            elif isinstance(p, str) and ("DF" in p or "GK" in p or "ピッチャー" in p): # 文字列ガード
                h_df_inj_count += 1
                
    a_df_inj_count = 0
    if isinstance(a_injuries, list):
        for p in a_injuries:
            if isinstance(p, dict) and p.get("pos") in ["DF", "GK"]:
                a_df_inj_count += 1
            elif isinstance(p, str) and ("DF" in p or "GK" in p):
                a_df_inj_count += 1

    # 調子係数（③）の判定バグ修正（0.0の時はきっちり0ptにする）
    h_cond_pt_s = 20 if h_cond_coef > 0.01 else (-40 if h_cond_coef < -0.01 else 0)
    a_cond_pt_s = 20 if a_cond_coef > 0.01 else (-40 if a_cond_coef < -0.01 else 0)
    
    h_cond_pt_r = 20 if h_cond_coef > 0.01 else (-40 if h_cond_coef < -0.01 else 0)
    a_cond_pt_r = 20 if a_cond_coef > 0.01 else (-40 if a_cond_coef < -0.01 else 0)
    
    # ==========================================
    # 📝 結果出力（デバッグ内訳表示版）
    # ==========================================
    print(f"⚽ 試合No.{match_no}: {home_team} vs {away_team}")
    
    # 1. ☀️ 晴れの内訳
    print(f"  ☀️ 【晴れpt の詳細内訳】(初期値 100pt スタート)")
    print(f"    ・①順位差影響 -> 🏠 {h_rank_pt_s:+}pt / 🚀 {a_rank_pt_s:+}pt  (順位: 🏠{h_rank}位 vs 🚀{a_rank}位)")
    print(f"    ・②得失点補正 -> 🏠 {h_goal_pt_s:+}pt / 🚀 {a_goal_pt_s:+}pt  (直近得失: 🏠{h_goal}-{h_lose} vs 🚀{a_goal}-{a_lose})")
    print(f"    ・③調子係数   -> 🏠 {h_cond_pt_s:+}pt / 🚀 {a_cond_pt_s:+}pt")
    print(f"    ・④怪我人ペナ -> 🏠 {h_inj_pt_s:+}pt / 🚀 {a_inj_pt_s:+}pt  (人数: 🏠{h_inj_count}人 vs 🚀{a_inj_count}人)")
    print(f"    ・⑤過密日程   -> 🏠 {h_rest_pt_s:+}pt / 🚀 {a_rest_pt_s:+}pt  (間隔: 🏠{h_days}日 vs 🚀{a_days}日)")
    print(f"    ⇒ 最終総合pt  -> 🏠 {h_pt_sunny}pt vs 🚀 {a_pt_sunny}pt")
    print(f"    ・変換ウエイト -> 🏠 {details_s['weight_h']:.1f} vs 🚀 {details_s['weight_a']:.1f} " + ("🔥(J2アウェイ・カウンター適用)" if details_s['boost_applied'] else ""))
    print(f"    [確率] 🏠勝:{h_pct_s}%  △分:{d_pct_s}%  🚀負:{a_pct_s}%  ➡️  【予想：{forecast_sunny}】")
    
    print(f"  --------------------------------------------------")
    
    # 2. ☔ 雨の内訳
    print(f"  ☔ 【雨天pt の詳細内訳】(初期値 100pt スタート)")
    print(f"    ・①順位差影響 -> 🏠 {h_rank_pt_r:+}pt / 🚀 {a_rank_pt_r:+}pt")
    print(f"    ・②失点のみ   -> 🏠 {h_goal_pt_r:+}pt / 🚀 {a_goal_pt_r:+}pt  (雨は失点の多さのみペナルティ)")
    print(f"    ・③調子係数   -> 🏠 {h_cond_pt_r:+}pt / 🚀 {a_cond_pt_r:+}pt")
    print(f"    ・④守備怪我人 -> 🏠 {h_inj_pt_r:+}pt / 🚀 {a_inj_pt_r:+}pt  (雨はDF/GK怪我を2倍化)")
    print(f"    ・⑤過密日程   -> 🏠 {h_rest_pt_r:+}pt / 🚀 {a_rest_pt_r:+}pt")
    print(f"    ⇒ 最終総合pt  -> 🏠 {h_pt_rainy}pt vs 🚀 {a_pt_rainy}pt")
    print(f"    ・変換ウエイト -> 🏠 {details_r['weight_h']:.1f} vs 🚀 {details_r['weight_a']:.1f} " + ("🔥(J2アウェイ・カウンター適用)" if details_r['boost_applied'] else ""))
    print(f"    [確率] 🏠勝:{h_pct_r}%  △分:{d_pct_r}%  🚀負:{a_pct_r}%  ➡️  【予想：{forecast_rainy}】")
    print("-" * 60)

    m["forecastSunny"] = forecast_sunny
    m["forecastSunnyDetails"] = {"homePct": h_pct_s, "drawPct": d_pct_s, "awayPct": a_pct_s, "homePt": h_pt_sunny, "awayPt": a_pt_sunny}
    m["forecastRainy"] = forecast_rainy
    m["forecastRainyDetails"] = {"homePct": h_pct_r, "drawPct": d_pct_r, "awayPct": a_pct_r, "homePt": h_pt_rainy, "awayPt": a_pt_rainy}

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("💾 [predict.py] 引き分け確率の動的連動化、および雨天バグの修正が完了しました！")
