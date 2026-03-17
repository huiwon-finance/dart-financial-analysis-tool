import pandas as pd
import streamlit as st
import OpenDartReader
import altair as alt

def get_value(df, keyword):

    # 안전장치: account_nm 없으면 None
    if df is None or df.empty or "account_nm" not in df.columns:
        return None

    row = df[df["account_nm"].astype(str).str.contains(keyword, na=False)]
    if row.empty:
        return None

    val = row.iloc[0].get("thstrm_amount", None)
    if val is None:
        return None

    try:
        return float(str(val).replace(",", ""))
    except ValueError:
        return None

def get_value_any(df, keywords):
    """
    여러 키워드 중 하나라도 매칭되면 값을 반환
    (값, 매칭된 키워드) 형태로 반환
    """
    for kw in keywords:
        v = get_value(df, kw)
        if v is not None:
            return v, kw
    return None, None


st.title("DART 기반 기업 재무 분석 대시보드")
st.caption("OpenDART 공시 데이터를 활용해 기업 재무비율을 분석하고 동종기업과 비교하는 도구입니다.")

api_key = "a05a055bad63e93f2823bf00c2d4556face87bae"
dart = OpenDartReader(api_key)

peer_groups = {
# =========================
# 반도체 / 전자
# =========================
"삼성전자": ["SK하이닉스", "DB하이텍"],
"SK하이닉스": ["삼성전자", "DB하이텍"],
"DB하이텍": ["삼성전자", "SK하이닉스"],

# =========================
# 방산 / 항공우주
# =========================
"LIG넥스원": ["한화에어로스페이스", "한국항공우주", "현대로템"],
"한화에어로스페이스": ["LIG넥스원", "한국항공우주", "현대로템"],
"한국항공우주": ["LIG넥스원", "한화에어로스페이스", "현대로템"],
"현대로템": ["LIG넥스원", "한화에어로스페이스", "한국항공우주"],

# =========================
# 자동차 / 완성차
# =========================
"기아": ["현대자동차", "KG모빌리티"],
"현대자동차": ["기아", "KG모빌리티"],
"KG모빌리티": ["현대자동차", "기아"],

# =========================
# 자동차 부품 / 모듈
# =========================
"현대모비스": ["HL만도", "한온시스템"],
"HL만도": ["현대모비스", "한온시스템"],
"한온시스템": ["현대모비스", "HL만도"],

# =========================
# 물류 / 유통 / 운송
# =========================
"현대글로비스": ["CJ대한통운", "한진"],
"CJ대한통운": ["현대글로비스", "한진"],
"한진": ["현대글로비스", "CJ대한통운"],

# =========================
# IT 서비스 / 디지털
# =========================
"현대오토에버": ["삼성SDS", "포스코DX"],
"삼성SDS": ["현대오토에버", "포스코DX"],
"포스코DX": ["현대오토에버", "삼성SDS"],
}




# 기업 검색 키워드 입력
search_keyword = st.text_input("기업명을 검색하세요", "삼성")

# DART 기업 목록 불러오기
corp_df = dart.corp_codes

# corp_name 컬럼 기준으로 검색
search_result = corp_df[corp_df["corp_name"].astype(str).str.contains(search_keyword, na=False)]

# 검색 결과가 있으면 선택창 제공
if not search_result.empty:
    selected_row = st.selectbox(
        "분석할 기업을 선택하세요",
        search_result.to_dict("records"),
        format_func=lambda x: x["corp_name"]
    )
    company_name = selected_row["corp_name"]
    corp_code = selected_row["corp_code"]
else:
    company_name = None
    corp_code = None
    st.warning("검색 결과가 없습니다. 다른 키워드를 입력해보세요.")

year = st.selectbox("분석 연도", ["2024", "2023", "2022"])



if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if "compare_clicked" not in st.session_state:
    st.session_state.compare_clicked = False

if st.button("재무 분석 시작"):
    if company_name is None:
        st.error("❌ 먼저 기업 검색 후 분석할 기업을 선택해 주세요.")
        st.stop()

    st.session_state.analysis_done = True
    st.session_state.compare_clicked = False


if st.session_state.analysis_done: 
    try:
        df = dart.finstate(corp_code, int(year))
    except Exception:
        st.error("❌ 기업명을 DART에서 찾지 못했습니다. 기업명을 다시 확인해 주세요.")
        st.stop()

    if df is None or df.empty:
        st.error("❌ 재무제표 데이터를 불러오지 못했습니다. 기업명/연도를 확인해 주세요.")
        st.stop()

# 필요한 값 추출
    debt = get_value(df, "부채총계")
    equity = get_value(df, "자본총계")
    assets = get_value(df, "자산총계")
    non_current_assets = get_value(df, "비유동자산")
    current_assets = get_value(df, "유동자산")
    current_liabilities = get_value(df, "유동부채")

    sales = get_value(df, "매출액")
    if sales is None:
        sales = get_value(df, "수익")

    operating_income = get_value(df, "영업이익")
    if operating_income is None:
        operating_income = get_value(df, "영업이익(손실)")  # 회사/표기 케이스 대응

    interest_expense, matched_interest = get_value_any(
        df,
        [
            "이자비용",
            "금융비용",
            "금융원가",
            "이자비용(금융원가)",
            "이자비용(금융비용)",
            "금융비용(이자)",
        ]
    )


    # 순이익 계정명은 회사마다 달라서 2개 키워드로 시도
    net_income = get_value(df, "순이익")
    if net_income is None:
        net_income = get_value(df, "당기순")

    missing = [] 
    if debt is None: missing.append("부채총계")
    if equity is None: missing.append("자본총계")
    if assets is None: missing.append("자산총계")
    if net_income is None: missing.append("순이익/당기순")
    if current_assets is None: missing.append("유동자산")
    if current_liabilities is None: missing.append("유동부채")
    if sales is None: missing.append("매출액/수익")
    if operating_income is None: missing.append("영업이익")
    if non_current_assets is None: missing.append("비유동자산")

    if missing:
        st.error(f"❌ 필요한 계정을 찾지 못했습니다: {', '.join(missing)}")
        st.stop()

    if equity == 0 or assets == 0:
        st.error("❌ 자본총계 또는 자산총계가 0이라 계산할 수 없습니다.")
        st.stop()
    if equity == 0 or assets == 0 or current_liabilities == 0 or sales == 0:
        st.error("❌ 분모(자본/자산/유동부채/매출)가 0이라 계산할 수 없습니다.")
        st.stop()

    # 비율 계산
    debt_ratio = (debt / equity) * 100
    equity_ratio = (equity / assets) * 100
    roe = (net_income / equity) * 100
    current_ratio = (current_assets / current_liabilities) * 100
    asset_turnover = sales / assets
    roa = (net_income / assets) * 100
    op_margin = (operating_income / sales) * 100
    interest_coverage = None
    if interest_expense is not None and interest_expense != 0:
        interest_coverage = operating_income / interest_expense
    current_asset_ratio = (current_assets / assets) * 100
    non_current_asset_ratio = (non_current_assets / assets) * 100



# 결과 표시 (⭐ 반드시 버튼 if문 안에 있어야 함)

    if st.session_state.analysis_done:

        st.subheader(f"🔍 {company_name} ({year}년) 분석 결과")

        tab_stab, tab_prof, tab_act = st.tabs(["🛡 안정성", "📈 수익성", "⚙ 활동성/자산구성"])

# ===================== 안정성 =====================
    with tab_stab:
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("부채비율", f"{debt_ratio:.2f}%")
        s2.metric("자기자본비율", f"{equity_ratio:.2f}%")
        s3.metric("유동비율", f"{current_ratio:.2f}%")
    if interest_coverage is not None:
        s4.metric("이자보상비율", f"{interest_coverage:.2f}배")
    else:
        s4.metric("이자보상비율", "N/A")

# ===================== 수익성 =====================
    with tab_prof:
        p1, p2, p3 = st.columns(3)
        p1.metric("ROE", f"{roe:.2f}%")
        p2.metric("ROA", f"{roa:.2f}%")
        p3.metric("영업이익률", f"{op_margin:.2f}%")

# ===================== 활동성/자산구성 =====================
    with tab_act:
        a1, a2, a3 = st.columns(3)
        a1.metric("총자산회전율", f"{asset_turnover:.2f}회")
        a2.metric("유동자산비중", f"{current_asset_ratio:.2f}%")
        a3.metric("비유동자산비중", f"{non_current_asset_ratio:.2f}%")

        st.caption("※ 고정자산회전율(매출/유형자산)은 finstate 본문 데이터에 '유형자산' 계정이 없어 산출하지 않았습니다. (추후 세부 계정/주석 연동 과제)")

    st.subheader("🤖 AI 재무 분석 결과")

    analysis = ""

    if debt_ratio < 100:
        analysis += "부채비율이 낮아 재무 안정성이 매우 우수합니다. "
    elif debt_ratio < 200:
        analysis += "부채비율이 적정 수준으로 안정적인 재무구조입니다. "
    else:
        analysis += "부채비율이 높아 재무 리스크 관리가 필요합니다. "

    if roe > 15:
        analysis += "ROE가 높아 수익성이 뛰어난 기업입니다. "
    elif roe > 5:
        analysis += "ROE가 안정적인 수준으로 양호한 수익성을 보입니다. "
    else:
        analysis += "ROE가 낮아 수익성 개선이 필요합니다. "

    if current_ratio >= 150:
        analysis += "유동비율이 높아 단기 지급능력이 양호합니다. "
    elif current_ratio >= 100:
        analysis += "유동비율이 100% 이상으로 단기 유동성은 안정적인 편입니다. "
    else:
        analysis += "유동비율이 100% 미만으로 단기 유동성 리스크를 점검할 필요가 있습니다. "

    if asset_turnover > 1:
        analysis += "자산 활용 효율이 높은 기업입니다. "
    elif asset_turnover > 0.5:
        analysis += "자산 활용은 평균적인 수준입니다. "
    else:
        analysis += "자산 활용 효율 개선이 필요합니다. "

    if roa > 7:
        analysis += "ROA가 높아 자산 대비 수익 창출력이 우수합니다. "
    elif roa > 3:
        analysis += "ROA가 양호한 수준으로 자산 활용이 안정적입니다. "
    else:
        analysis += "ROA가 낮아 자산 효율 개선 여지가 있습니다. "

    if op_margin > 10:
        analysis += "영업이익률이 높아 본업 경쟁력이 우수합니다. "
    elif op_margin > 3:
        analysis += "영업이익률이 양호한 수준입니다. "
    else:
        analysis += "영업이익률이 낮아 수익구조 점검이 필요합니다. "

    if interest_coverage is None:
        analysis += "이자비용 항목이 재무제표 본문에서 확인되지 않아 이자보상비율은 산출하지 않았습니다(주석 필요). "
    else:
        if interest_coverage >= 5:
            analysis += "이자보상비율이 높아 이자 지급 여력이 충분합니다. "
        elif interest_coverage >= 1.5:
            analysis += "이자보상비율이 보통 수준입니다. "
        else:
            analysis += "이자보상비율이 낮아 이자부담 리스크가 있습니다. "

    # 자산구성 해석
    if non_current_asset_ratio >= 50:
        analysis += "비유동자산 비중이 높아 설비 및 장기 투자자산 비중이 큰 구조로 해석됩니다. "
    else:
        analysis += "유동자산 비중이 상대적으로 높아 운전자본 중심의 자산 구조를 보입니다. "

    # 산업 분류
    name = company_name.strip()

    semiconductor = ["삼성전자", "SK하이닉스", "DB하이텍"]
    defense = ["LIG넥스원", "한화에어로스페이스", "한국항공우주"]
    auto = ["현대자동차", "기아", "KG모빌리티"]
    logistics = ["현대글로비스", "CJ대한통운", "한진"]
    it_service = ["현대오토에버", "삼성SDS", "포스코DX"]
    auto_parts = ["현대모비스", "HL만도", "한온시스템", "현대위아"]

    if name in semiconductor:
        analysis += "반도체 산업은 대규모 설비투자가 핵심이므로 비유동자산 비중이 높은 구조가 일반적입니다."
    elif name in defense:
        analysis += "방산 산업은 장기 프로젝트 기반 사업 구조로 안정적인 수주와 설비 투자 비중이 특징입니다."
    elif name in auto:
        analysis += "자동차 산업은 생산설비와 제조 인프라 투자가 중요한 제조업 구조로 해석됩니다."
    elif name in auto_parts:
        analysis += "자동차 부품 산업은 완성차 업체와의 공급망 연계가 중요하며, 생산설비와 품질·원가 경쟁력이 핵심인 제조업 구조로 해석됩니다."
    elif name in logistics:
        analysis += "물류 산업은 운송 인프라와 운영 효율성이 중요한 산업 구조를 보입니다."
    elif name in it_service:
        analysis += "IT 서비스 산업은 시스템 구축과 운영 기반 사업 구조로 안정적인 수익 구조와 인건비 중심 비용 구조가 특징입니다."

    st.success(analysis)

    with st.expander("🔍 AI 분석 근거 보기"):
        st.markdown("### 1) 사용 지표 & 산식")
        st.write(f"- 부채비율 = 부채총계 / 자본총계 × 100 = {debt_ratio:.2f}%")
        st.write(f"- 자기자본비율 = 자본총계 / 자산총계 × 100 = {equity_ratio:.2f}%")
        st.write(f"- ROE = 당기순이익 / 자본총계 × 100 = {roe:.2f}%")
        st.write(f"- 유동비율 = 유동자산 / 유동부채 × 100 = {current_ratio:.2f}%")
        st.write(f"- 총자산회전율 = 매출액 / 자산총계 = {asset_turnover:.2f}회")
        st.write(f"- ROA = 당기순이익 / 자산총계 × 100 = {roa:.2f}%")
        st.write(f"- 이자비용 매칭 결과: {matched_interest if matched_interest else '재무제표 본문에서 미검출(주석 필요)'}")

        st.markdown("### 2) 판정 기준")
        st.write("부채비율: <100 우수 / 100~200 적정 / ≥200 리스크")
        st.write("ROE: >15 우수 / 5~15 양호 / ≤5 개선 필요")
        st.write("유동비율: ≥150 양호 / 100~150 보통 / <100 점검 필요")
        st.write("총자산회전율: >1.0 높음 / 0.5~1.0 평균 / <0.5 개선 필요")
        st.write("ROA: >7 우수 / 3~7 양호 / ≤3 개선 필요")

        st.markdown("### 3) 이번 결과 적용 근거")

        if debt_ratio < 100:
            st.success(f"부채비율 {debt_ratio:.2f}% → 우수")
        elif debt_ratio < 200:
            st.warning(f"부채비율 {debt_ratio:.2f}% → 적정")
        else:
            st.error(f"부채비율 {debt_ratio:.2f}% → 리스크")

        if roe > 15:
            st.success(f"ROE {roe:.2f}% → 우수")
        elif roe > 5:
            st.info(f"ROE {roe:.2f}% → 양호")
        else:
            st.warning(f"ROE {roe:.2f}% → 개선 필요")

        if current_ratio >= 150:
            st.success(f"유동비율 {current_ratio:.2f}% → 양호")
        elif current_ratio >= 100:
            st.info(f"유동비율 {current_ratio:.2f}% → 보통")
        else:
            st.warning(f"유동비율 {current_ratio:.2f}% → 점검 필요")

        if asset_turnover > 1:
            st.success(f"총자산회전율 {asset_turnover:.2f}회 → 높음")
        elif asset_turnover > 0.5:
            st.info(f"총자산회전율 {asset_turnover:.2f}회 → 평균")
        else:
            st.warning(f"총자산회전율 {asset_turnover:.2f}회 → 개선 필요")

        if roa > 7:
            st.success(f"ROA {roa:.2f}% → 우수")
        elif roa > 3:
            st.info(f"ROA {roa:.2f}% → 양호")
        else:
            st.warning(f"ROA {roa:.2f}% → 개선 필요")

        if current_ratio >= 150:
            st.success(f"유동비율 {current_ratio:.2f}% → 양호")
        elif current_ratio >= 100:
            st.info(f"유동비율 {current_ratio:.2f}% → 보통")
        else:
            st.warning(f"유동비율 {current_ratio:.2f}% → 점검 필요")

        if asset_turnover > 1:
            st.success(f"총자산회전율 {asset_turnover:.2f}회 → 높음")
        elif asset_turnover > 0.5:
            st.info(f"총자산회전율 {asset_turnover:.2f}회 → 평균")
        else:
            st.warning(f"총자산회전율 {asset_turnover:.2f}회 → 개선 필요")
        if roa > 7:
            st.success(f"ROA {roa:.2f}% → 우수")
        elif roa > 3:
            st.info(f"ROA {roa:.2f}% → 양호")
        else:
            st.warning(f"ROA {roa:.2f}% → 개선 필요")

st.info("차입금 의존도, 이자보상비율 등은 주석 데이터를 추가로 분석해야 합니다.")

st.subheader("🤝 비교 분석")

if company_name in peer_groups:
    if st.button("동종기업 자동 비교"):

        compare_results = []

        # 기준 기업 먼저 추가
        compare_results.append({
            "기업명": company_name,
            "ROE": roe,
            "ROA": roa,
            "영업이익률": op_margin,
            "부채비율": debt_ratio
        })

        for peer in peer_groups[company_name]:
            try:
                peer_df = dart.finstate(peer, int(year))

                if peer_df is None or peer_df.empty:
                    continue

                peer_debt = get_value(peer_df, "부채총계")
                peer_equity = get_value(peer_df, "자본총계")
                peer_assets = get_value(peer_df, "자산총계")
                peer_sales = get_value(peer_df, "매출액")
                if peer_sales is None:
                    peer_sales = get_value(peer_df, "수익")

                peer_net_income = get_value(peer_df, "순이익")
                if peer_net_income is None:
                    peer_net_income = get_value(peer_df, "당기순")

                peer_operating_income = get_value(peer_df, "영업이익")
                if peer_operating_income is None:
                    peer_operating_income = get_value(peer_df, "영업이익(손실)")

                if None in [peer_debt, peer_equity, peer_assets, peer_sales, peer_net_income, peer_operating_income]:
                    continue

                if peer_equity == 0 or peer_assets == 0 or peer_sales == 0:
                    continue

                peer_roe = (peer_net_income / peer_equity) * 100
                peer_roa = (peer_net_income / peer_assets) * 100
                peer_op_margin = (peer_operating_income / peer_sales) * 100
                peer_debt_ratio = (peer_debt / peer_equity) * 100

                compare_results.append({
                    "기업명": peer,
                    "ROE": round(peer_roe, 2),
                    "ROA": round(peer_roa, 2),
                    "영업이익률": round(peer_op_margin, 2),
                    "부채비율": round(peer_debt_ratio, 2)
                })

            except:
                continue

        if len(compare_results) > 1:
            compare_df = pd.DataFrame(compare_results)

            st.write("### 동종기업 비교 결과")
            st.dataframe(compare_df, use_container_width=True)
            
            compare_df = compare_df.set_index("기업명")
            compare_df = compare_df.loc[[company_name] + [c for c in compare_df.index if c != company_name]]
            chart_df = compare_df.reset_index()

            st.subheader("📊 동종기업 ROE 비교")
            roe_chart = alt.Chart(chart_df).mark_bar().encode(
                x=alt.X("기업명:N", sort=chart_df["기업명"].tolist()),
                y="ROE:Q"
            )
            st.altair_chart(roe_chart, use_container_width=True)

            st.subheader("📊 동종기업 영업이익률 비교")
            op_chart = alt.Chart(chart_df).mark_bar().encode(
                x=alt.X("기업명:N", sort=chart_df["기업명"].tolist()),
                y="영업이익률:Q"
            )
            st.altair_chart(op_chart, use_container_width=True)

            base = compare_df.iloc[0]

            avg_roe = compare_df["ROE"].mean()
            avg_roa = compare_df["ROA"].mean()
            avg_op = compare_df["영업이익률"].mean()
            avg_debt = compare_df["부채비율"].mean()

            compare_analysis = ""

            if base["ROE"] > avg_roe:
                compare_analysis += "동종기업 평균 대비 ROE가 높아 자기자본 수익성이 우수합니다. "
            else:
                compare_analysis += "동종기업 평균 대비 ROE가 낮아 수익성 개선 여지가 있습니다. "

            if base["ROA"] > avg_roa:
                compare_analysis += "ROA도 평균 대비 높아 자산 활용 효율이 양호합니다. "
            else:
                compare_analysis += "ROA는 평균 대비 낮아 자산 효율성 점검이 필요합니다. "

            if base["영업이익률"] > avg_op:
                compare_analysis += "영업이익률이 동종기업 대비 높아 본업 경쟁력이 우수합니다. "
            else:
                compare_analysis += "영업이익률이 평균 대비 낮아 본업 수익성 개선이 필요합니다. "

            if base["부채비율"] < avg_debt:
                compare_analysis += "부채비율이 평균보다 낮아 재무 안정성이 상대적으로 우수합니다."
            else:
        
                compare_analysis += "부채비율이 평균보다 높아 재무구조 관리가 필요합니다."
    
        

            st.success(compare_analysis)
        else:
            st.warning("비교 가능한 동종기업 데이터를 충분히 불러오지 못했습니다.")
else:
    st.info("현재 이 기업에 대한 동종기업 비교군은 아직 설정되지 않았습니다.")