#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
절(節) 분절과 은유 판정 대상 추출

두 저본이 각자의 방식으로 표시한 경계를 그대로 써서 절을 나눈다.
  - 「화식열전」(中國哲學書電子化計劃 표점본): 표점(，。：；！？、괄호류)
  - 열하일기(한국고전번역원 연암집 원문): 저본의 띄어쓰기

판정 대상은 트리거 41개를 포함한 절과 그 앞뒤 각 1절이며,
두 문헌에 같은 규칙을 적용한다.

사용법
    python segment_clauses.py --data ./data --out clauses.csv

출력 열
    문헌, 텍스트, 문단번호, 절번호, 절원문, 글자수, 트리거, 판정대상
"""
import argparse
import csv
import re
import sys
from pathlib import Path

import pandas as pd

# ── 트리거 목록 (부록 표 2와 동일) ────────────────────────────────
TRIGGER_SINGLE = "財貨利富貧買賣銀錢商賈價資產産殖稅賦貢儉奢窖券契倍息債償贖什贏羨"
TRIGGER_COMPOUND = ["貿易", "典當", "包銀", "千金", "萬金", "素封", "貨殖", "財幣", "財貨"]

# 「화식열전」 표점본의 절 경계 문자
PUNCT = r"[，。：；！？、「」『』（）\s]+"

# 열하일기 편명 대응 (원문 파일의 한자 편명 → 한글 편명)
YEOLHA_CHAPTERS = {
    "渡江錄": "도강록",
    "盛京雜識": "성경잡지",
    "馹汛隨筆": "일신수필",
    "關內程史": "관내정사",
    "行在雜錄": "행재잡록",
    "審勢編": "심세편",
    "玉匣夜話": "옥갑야화",
}

# 출력 순서
TEXT_ORDER = [
    "화식열전", "도강록", "성경잡지", "일신수필",
    "관내정사", "옥갑야화", "행재잡록", "심세편",
]


def hanja_only(s: str) -> str:
    """한자만 남긴다. 이체자는 정규화하지 않고 저본 표기를 따른다."""
    return re.sub(r"[^\u4e00-\u9fff]", "", str(s))


def matched_triggers(clause: str) -> list:
    """절에 포함된 트리거를 찾는다. 복합어를 먼저 잡고, 그 안에 든 단일자는 제외한다."""
    found = [w for w in TRIGGER_COMPOUND if w in clause]
    found += [c for c in TRIGGER_SINGLE
              if c in clause and not any(c in w for w in found)]
    return found


def segment_huozhi(path: Path) -> list:
    """「화식열전」을 표점 단위로 나눈다."""
    df = pd.read_excel(path)
    out = []
    for _, row in df.iterrows():
        para = int(row["문단번호"])
        for i, piece in enumerate(re.split(PUNCT, str(row["원문(原文)"])), start=1):
            clause = hanja_only(piece)
            if clause:
                out.append(("사기", "화식열전", para, i, clause))
    return out


def segment_yeolha(path: Path) -> list:
    """열하일기를 저본의 띄어쓰기 단위로 나눈다."""
    df = pd.read_excel(path, sheet_name="전체")
    out = []
    for _, row in df.iterrows():
        name = YEOLHA_CHAPTERS.get(row["편(篇)"])
        if name is None:
            continue
        para = int(row["문단번호"])
        for i, piece in enumerate(str(row["원문(原文)"]).split(), start=1):
            clause = hanja_only(piece)
            if clause:
                out.append(("열하일기", name, para, i, clause))
    return out


def mark_targets(rows: list) -> list:
    """텍스트별로 트리거 절과 그 앞뒤 1절을 판정 대상으로 표시한다."""
    marked = []
    for text in TEXT_ORDER:
        sub = [r for r in rows if r[1] == text]
        hit = {i for i, r in enumerate(sub) if matched_triggers(r[4])}
        window = {i for j in hit for i in (j - 1, j, j + 1) if 0 <= i < len(sub)}
        for i, r in enumerate(sub):
            trig = " ".join(matched_triggers(r[4]))
            marked.append((*r, len(r[4]), trig, "Y" if i in window else ""))
    return marked


def main() -> int:
    ap = argparse.ArgumentParser(description="절 분절과 판정 대상 추출")
    ap.add_argument("--data", default="./data", help="원문 엑셀이 있는 폴더")
    ap.add_argument("--out", default="clauses.csv", help="출력 CSV 경로")
    args = ap.parse_args()

    data = Path(args.data)
    hz = data / "사기_화식열전_원문.xlsx"
    yh = data / "열하일기_원문.xlsx"
    for p in (hz, yh):
        if not p.exists():
            print(f"원문 파일을 찾을 수 없습니다: {p}", file=sys.stderr)
            return 1

    rows = segment_huozhi(hz) + segment_yeolha(yh)
    marked = mark_targets(rows)

    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["문헌", "텍스트", "문단번호", "절번호", "절원문",
                    "글자수", "트리거", "판정대상"])
        w.writerows(marked)

    print(f"{args.out} 저장")
    print(f"{'텍스트':<10}{'전체 절':>8}{'판정 대상':>10}{'평균 글자수':>12}")
    total_all = total_tgt = 0
    for text in TEXT_ORDER:
        sub = [r for r in marked if r[1] == text]
        tgt = [r for r in sub if r[7] == "Y"]
        avg = sum(r[5] for r in sub) / len(sub)
        print(f"{text:<10}{len(sub):>8}{len(tgt):>10}{avg:>12.2f}")
        total_all += len(sub)
        total_tgt += len(tgt)
    print(f"{'합계':<10}{total_all:>8}{total_tgt:>10}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
