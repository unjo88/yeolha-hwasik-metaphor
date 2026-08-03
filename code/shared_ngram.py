#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
저빈도 표현 공유 검색과 대조 코퍼스 검증

1단계 「화식열전」에서 2~6자 n-gram을 모두 추출하여 열하일기에 출현하는 것을 찾고,
       더 긴 공유 표현에 포함되는 짧은 것을 제거한다.
2단계 그 결과를 무경칠서·사서집주 대조 코퍼스에 대조하여, 반복 출현하는
       일반 한문 문어 표현을 걸러 낸다.

사용법
    python shared_ngram.py --data ./data --out shared.csv
"""
import argparse, csv, re, sys
from collections import Counter
from pathlib import Path
import pandas as pd

HAN = lambda s: re.sub(r"[^\u4e00-\u9fff]", "", str(s))
YEOLHA = {"渡江錄","盛京雜識","馹汛隨筆","關內程史","行在雜錄","審勢編","玉匣夜話"}


def load(path, sheet=None, col="원문(原文)"):
    df = pd.read_excel(path, sheet_name=sheet) if sheet else pd.read_excel(path)
    return [HAN(x) for x in df[col]]


def maximal_shared(units, target, nmin=2, nmax=6):
    """units의 n-gram 중 target에 나타나는 것을 찾고 극대 표현만 남긴다."""
    shared = {}
    for n in range(nmin, nmax + 1):
        cnt = Counter()
        for u in units:
            for i in range(len(u) - n + 1):
                cnt[u[i:i + n]] += 1
        for g, c in cnt.items():
            if g in target:
                shared[g] = (n, c, target.count(g))
    keep = []
    for g in sorted(shared, key=len, reverse=True):
        if not any(g in longer and g != longer for longer in keep):
            keep.append(g)
    return [(g, *shared[g]) for g in keep]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="./data")
    ap.add_argument("--out", default="shared.csv")
    ap.add_argument("--min-len", type=int, default=3, help="보고할 최소 글자수")
    a = ap.parse_args()
    d = Path(a.data)
    try:
        hz_units = load(d / "사기_화식열전_원문.xlsx")
        yh_df = pd.read_excel(d / "열하일기_원문.xlsx", sheet_name="전체")
        yh = "".join(HAN(r["원문(原文)"]) for _, r in yh_df.iterrows()
                     if r["편(篇)"] in YEOLHA)
        mu = "".join(load(d / "무경칠서_원문.xlsx"))
        sa = "".join(load(d / "사서집주_원문.xlsx"))
    except FileNotFoundError as e:
        print(f"원문 파일을 찾을 수 없습니다: {e}", file=sys.stderr)
        return 1

    rows = [r for r in maximal_shared(hz_units, yh) if r[1] >= a.min_len]
    rows.sort(key=lambda r: (-r[1], r[3]))

    with open(a.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["표현", "글자수", "화식열전", "열하일기", "무경칠서", "사서집주", "판정"])
        for g, n, hc, yc in rows:
            m, s = mu.count(g), sa.count(g)
            verdict = "대조 코퍼스 미출현" if m + s == 0 else ("극소" if m + s <= 2 else "상용")
            w.writerow([g, n, hc, yc, m, s, verdict])

    print(f"{a.out} 저장 — {a.min_len}자 이상 공유 표현 {len(rows)}종")
    print(f"대조 코퍼스 무경칠서 {len(mu):,}자 · 사서집주 {len(sa):,}자")
    print("주의: 두 대조 코퍼스는 병서와 유가 경전으로 재화·물산을 다루지 않는다.")
    print("      따라서 재화 어휘의 미출현은 희소성의 증거가 되지 못한다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
