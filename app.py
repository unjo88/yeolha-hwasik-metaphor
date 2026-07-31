"""감각성 지수 재현 실행 환경 (Streamlit).

논문에 제시한 어휘 목록과 추출 절차만으로 감각성 지수가 재현되는지를
독자가 직접 확인할 수 있도록 만든 도구이다. 어휘 목록을 고쳐 넣으면
지수가 어떻게 달라지는지도 볼 수 있다.
"""

import pandas as pd
import streamlit as st

from concreteness import (
    A_LIST, B_LIST, TRIGGER_COMPOUND, TRIGGER_SINGLE,
    Lexicon, build_dataset, load_corpus, summarize,
)

st.set_page_config(page_title="감각성 지수 재현", layout="wide")

st.title("감각성 지수 재현")
st.caption(
    "한·중 고전문헌에 나타난 재화 인식의 언어문화적 재맥락화 고찰 — "
    "열하일기와 사기의 재화 관련 은유를 중심으로"
)

st.markdown(
    "논문 부록에 제시한 트리거 단어와 A·B 어휘 목록, 문맥 추출 절차만으로 "
    "감각성 지수를 다시 계산한다. 왼쪽에서 어휘 목록을 고치면 결과가 즉시 바뀐다."
)

with st.sidebar:
    st.header("어휘 목록")
    st.caption("공백으로 구분한다. 논문 게재 목록이 기본값이다.")
    ts = st.text_area("트리거 단어(단일자)", " ".join(TRIGGER_SINGLE), height=90)
    tc = st.text_area("트리거 단어(복합어)", " ".join(TRIGGER_COMPOUND), height=60)
    al = st.text_area("A 목록 — 감각적·실물적", " ".join(A_LIST), height=140)
    bl = st.text_area("B 목록 — 추상적·규범적", " ".join(B_LIST), height=110)
    if st.button("기본값으로 되돌리기"):
        st.rerun()

lex = Lexicon(ts.split(), tc.split(), al.split(), bl.split())

c1, c2, c3, c4 = st.columns(4)
c1.metric("트리거 단일자", len(lex.trigger_single))
c2.metric("트리거 복합어", len(lex.trigger_compound))
c3.metric("A 목록", len(lex.a_list))
c4.metric("B 목록", len(lex.b_list))


@st.cache_data(show_spinner="원문을 불러오는 중")
def _corpus():
    return load_corpus()


dataset = build_dataset(_corpus(), lex)
summary = summarize(dataset)

st.subheader("텍스트별 산출 결과")
st.caption("논문 <부록 표 5>에 해당한다. 차이 열이 0이면 게재치와 일치한다.")


def _mark(row):
    diff = row.get("차이")
    if pd.isna(diff):
        return [""] * len(row)
    color = "background-color:#e8f4ea" if abs(diff) < 0.05 else "background-color:#fdece8"
    return [color] * len(row)


st.dataframe(summary.style.apply(_mark, axis=1), use_container_width=True, hide_index=True)

matched = int((summary["차이"].abs() < 0.05).sum())
total = int(summary["차이"].notna().sum())
st.success(f"논문 게재치와 일치하는 항목 {matched} / {total}")

st.subheader("추출 문맥 전체")
st.caption(
    "트리거 단어로 추출한 재화 관련 문맥과 문맥별 A·B 빈도이다. "
    "A출현자·B출현자 열은 어떤 글자가 몇 번 계수되었는지를 보여 준다."
)

pick = st.multiselect(
    "텍스트 선택", sorted(dataset["텍스트"].unique()),
    default=sorted(dataset["텍스트"].unique()),
)
view = dataset[dataset["텍스트"].isin(pick)]
st.dataframe(view, use_container_width=True, hide_index=True, height=420)

st.download_button(
    "추출 문맥 자료 내려받기 (CSV)",
    view.to_csv(index=False).encode("utf-8-sig"),
    file_name="concreteness_contexts.csv",
    mime="text/csv",
)

with st.expander("산출 절차"):
    st.markdown(
        """
**열하일기** 원문을 공백 단위 어구로 분절한 뒤, 트리거 단어가 포함된 어구와
그 앞뒤 각 1개 어구를 묶어 재화 관련 문맥으로 삼는다. 인접하거나 겹치는
구간은 병합한다.

**화식열전** 표점본을 「。」 단위로 분절한 뒤, 트리거 단어가 포함된 문장을
문맥으로 삼는다.

**지수** 감각성 지수(%) = A ÷ (A + B) × 100

A·B 판정은 문맥별 개별 판정이 아니라 사전에 확정한 어휘 목록에 따라 일괄
적용한다. 빈도는 글자 단위 출현형을 기준으로 세며, 같은 글자가 반복되면
각 출현을 개별적으로 계산한다. A·B 어느 목록에도 없는 글자는 산출에서
제외한다. 「심세편」은 추출 문맥이 7건(A=0)에 그쳐 정량 비교에서 제외하였다.
        """
    )
