"""감각성 지수(Concreteness Index) 산출 모듈.

논문 부록에 제시한 절차를 그대로 구현한다.

  열하일기 : 원문을 공백 단위 어구로 분절 → 트리거 단어가 포함된 어구와
             그 앞뒤 각 1개 어구를 묶어 문맥으로 추출 → 인접·중복 구간 병합
  화식열전 : 「。」 단위로 문장을 분절 → 트리거 단어가 포함된 문장을 추출

  감각성 지수(%) = A ÷ (A + B) × 100

A·B 판정은 문맥별 개별 판정이 아니라 사전에 확정한 어휘 목록에 따라
일괄 적용한다. 빈도는 글자 단위 출현형을 기준으로 세며, 반복 출현은
각각 계산한다. A·B 어느 목록에도 없는 글자는 산출에서 제외한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

TRIGGER_SINGLE = "財 貨 利 富 貧 買 賣 銀 錢 商 賈 價 資 産 產 殖 稅 賦 貢 儉 奢 窖 券 契 倍 息 債 償 贖 什 贏 羨".split()
TRIGGER_COMPOUND = "貿易 典當 包銀 千金 萬金 素封 貨殖 財幣 財貨".split()

A_LIST = (
    "汗 甓 車 稻 銀 錢 金 鹽 鐵 穀 布 絲 米 麥 牛 馬 舟 船 瓦 木 材 屋 珠 玉 貂 參 桑 麻 薥 黍 "
    "酒 茶 衣 冠 履 鞍 轎 窯 粟 糧 魚 鹿 豕 猪 羊 鷄 鵝 薪 炭 漆 綿 緞 紬 絹 皮 甎 甃 甑 甕 罐 缸 甲 盆 缶"
).split()

B_LIST = (
    "義 禮 智 德 恩 惠 權 名 分 節 廉 恥 忠 孝 信 仁 誠 虛 姦 弊 道 理 法 制 私 公 欲 情 志 識 "
    "文 武 貴 賤 奢 儉 僞 詐 妄 罪 賊 盜"
).split()

# 논문 게재치 (본문 <표 6> 및 <부록 표 5>)
PUBLISHED = {
    "화식열전": 46.7, "도강록": 56.9, "관내정사": 45.1, "옥갑야화": 66.3,
    "행재잡록": 70.6, "성경잡지": 47.9, "일신수필": 60.9,
}

YEOLHA_SHEETS = {
    "도강록": "1권_도강록", "성경잡지": "2권_성경잡지", "일신수필": "3권_일신수필",
    "관내정사": "4권_관내정사", "행재잡록": "12권_행재잡록", "심세편": "14권_심세편",
    "옥갑야화": "20권_옥갑야화",
}


@dataclass
class Lexicon:
    trigger_single: list[str] = field(default_factory=lambda: list(TRIGGER_SINGLE))
    trigger_compound: list[str] = field(default_factory=lambda: list(TRIGGER_COMPOUND))
    a_list: list[str] = field(default_factory=lambda: list(A_LIST))
    b_list: list[str] = field(default_factory=lambda: list(B_LIST))

    def has_trigger(self, s: str) -> bool:
        if any(c in s for c in self.trigger_compound):
            return True
        return any(ch in s for ch in self.trigger_single)

    def count_ab(self, s: str) -> tuple[int, int]:
        a = sum(s.count(ch) for ch in self.a_list)
        b = sum(s.count(ch) for ch in self.b_list)
        return a, b

    def hits(self, s: str, pool: list[str]) -> str:
        out = []
        for ch in pool:
            n = s.count(ch)
            if n:
                out.append(ch + (f"×{n}" if n > 1 else ""))
        return " ".join(out)


def load_corpus(data_dir: Path = DATA_DIR) -> dict[str, str]:
    """텍스트명 → 원문 전체 문자열."""
    texts: dict[str, str] = {}
    yeolha = data_dir / "열하일기_원문.xlsx"
    for name, sheet in YEOLHA_SHEETS.items():
        df = pd.read_excel(yeolha, sheet_name=sheet)
        texts[name] = " ".join(str(v) for v in df["원문(原文)"].dropna())
    df = pd.read_excel(data_dir / "사기_화식열전_원문.xlsx", sheet_name="화식열전 원문")
    texts["화식열전"] = " ".join(str(v) for v in df["원문(原文)"].dropna())
    return texts


def extract_phrase_contexts(text: str, lex: Lexicon) -> list[str]:
    """열하일기: 어구 단위 문맥 추출(앞뒤 1어구, 인접 병합)."""
    tokens = [t for t in re.split(r"\s+", text) if t]
    spans: list[tuple[int, int]] = []
    for i, tok in enumerate(tokens):
        if lex.has_trigger(tok):
            spans.append((max(0, i - 1), min(len(tokens) - 1, i + 1)))
    merged: list[list[int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1] + 1:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return [" ".join(tokens[s:e + 1]) for s, e in merged]


def extract_sentence_contexts(text: str, lex: Lexicon) -> list[str]:
    """화식열전: 「。」 단위 문장 추출."""
    sentences = [s.strip() for s in re.split(r"[。]", text) if s.strip()]
    return [s for s in sentences if lex.has_trigger(s)]


def build_dataset(texts: dict[str, str], lex: Lexicon) -> pd.DataFrame:
    rows = []
    for name, text in texts.items():
        if name == "화식열전":
            unit, contexts = "문장", extract_sentence_contexts(text, lex)
            source = "사기"
        else:
            unit, contexts = "어구", extract_phrase_contexts(text, lex)
            source = "열하일기"
        for i, ctx in enumerate(contexts, 1):
            a, b = lex.count_ab(ctx)
            rows.append({
                "문헌": source, "텍스트": name, "분석단위": unit,
                "문맥코드": f"{name[:2]}-{i:03d}", "추출문맥(원문)": ctx,
                "A빈도": a, "B빈도": b,
                "A출현자": lex.hits(ctx, lex.a_list),
                "B출현자": lex.hits(ctx, lex.b_list),
            })
    return pd.DataFrame(rows)


def summarize(dataset: pd.DataFrame) -> pd.DataFrame:
    order = ["화식열전", "도강록", "관내정사", "옥갑야화", "행재잡록", "성경잡지", "일신수필", "심세편"]
    rows = []
    for name in order:
        part = dataset[dataset["텍스트"] == name]
        if part.empty:
            continue
        a, b = int(part["A빈도"].sum()), int(part["B빈도"].sum())
        idx = round(100 * a / (a + b), 1) if a + b else None
        pub = PUBLISHED.get(name)
        rows.append({
            "텍스트": name, "재화 문맥 추출수": len(part), "A(감각적)": a, "B(추상적)": b,
            "감각성 지수(%)": idx, "논문 게재치(%)": pub,
            "차이": None if (idx is None or pub is None) else round(idx - pub, 1),
        })
    six = dataset[~dataset["텍스트"].isin(["화식열전", "심세편"])]
    a, b = int(six["A빈도"].sum()), int(six["B빈도"].sum())
    rows.append({
        "텍스트": "열하일기 6편 합계", "재화 문맥 추출수": len(six), "A(감각적)": a, "B(추상적)": b,
        "감각성 지수(%)": round(100 * a / (a + b), 1), "논문 게재치(%)": 56.4,
        "차이": round(100 * a / (a + b) - 56.4, 1),
    })
    return pd.DataFrame(rows)


def reproduce(data_dir: Path = DATA_DIR, lex: Lexicon | None = None):
    lex = lex or Lexicon()
    dataset = build_dataset(load_corpus(data_dir), lex)
    return dataset, summarize(dataset)


if __name__ == "__main__":
    ds, summary = reproduce()
    print(summary.to_string(index=False))
    print(f"\n총 추출 문맥 {len(ds)}건")
