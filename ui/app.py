import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import build_graph

st.set_page_config(page_title="AI Loan Approval POC", page_icon="🏦", layout="centered")

st.title("🏦 AI Loan Approval System")
st.caption("Two-Agent + Docker Sandbox Proof of Concept")
st.divider()

st.subheader("Applicant Information")

with st.form("loan_form"):
    customer_id = st.text_input("Customer ID", value="CUST001")

    col1, col2 = st.columns(2)
    with col1:
        salary = st.number_input("Monthly Salary (₹)", min_value=1.0, value=80000.0, step=5000.0)
        cibil_score = st.number_input("CIBIL Score", min_value=300, max_value=900, value=742, step=1)
        active_loans = st.number_input("Active Loans", min_value=0, value=1, step=1)
        payment_defaults = st.number_input("Payment Defaults", min_value=0, value=0, step=1)
    with col2:
        outstanding = st.number_input("Outstanding Loan Amount (₹)", min_value=0.0, value=125000.0, step=5000.0)
        requested = st.number_input("Requested Loan Amount (₹)", min_value=10000.0, value=500000.0, step=10000.0)
        rate = st.number_input("Annual Interest Rate (%)", min_value=0.0, value=10.5, step=0.5)
        tenure = st.number_input("Tenure (Months)", min_value=1, max_value=360, value=60, step=6)

    submitted = st.form_submit_button("🔍 Check Loan Eligibility", use_container_width=True, type="primary")

if submitted:
    customer = {
        "customer_id": customer_id,
        "monthly_salary": salary,
        "cibil_score": cibil_score,
        "active_loans": active_loans,
        "outstanding_amount": outstanding,
        "payment_defaults": payment_defaults,
        "requested_amount": requested,
        "annual_interest_rate": rate,
        "tenure_months": tenure,
    }

    app = build_graph()

    with st.status("Running multi-agent loan assessment...", expanded=True) as status:
        st.write("🤖 Agent 1: CIBIL Agent")
        try:
            # Run the first node so the UI can show the two-agent flow clearly.
            from main import cibil_agent, loan_decision_agent
            state = cibil_agent({"customer": customer})
            cibil = state["cibil_result"]
            st.write(f"CIBIL assessment: **{cibil['status']}**")

            st.write("🤖 Agent 2: Loan Decision Agent")
            st.write("🐳 Docker Sandbox: calculating EMI with network disabled")
            result = loan_decision_agent(state)
            status.update(label="Assessment completed", state="complete")
        except Exception as exc:
            status.update(label="Assessment failed", state="error")
            st.error(f"Could not complete the assessment: {exc}")
            st.stop()

    st.divider()
    st.subheader("📊 CIBIL Agent Result")
    c1, c2, c3 = st.columns(3)
    c1.metric("CIBIL Score", cibil["score"])
    c2.metric("CIBIL Status", cibil["status"])
    c3.metric("Payment Defaults", cibil["payment_defaults"])

    st.subheader("🏦 Loan Decision")
    decision = result["final_decision"]
    if decision == "APPROVED":
        st.success(f"## ✅ {decision}")
    else:
        st.error(f"## ❌ {decision}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Requested Loan", f"₹{requested:,.0f}")
    c2.metric("Monthly EMI", f"₹{result['emi']:,.2f}")
    c3.metric("EMI / Salary", f"{result['loan_result']['emi_ratio']:.1%}")

    st.info(result["reason"])

    with st.expander("🔧 Technical POC Details"):
        st.write("**Agent 1:** CIBIL Agent")
        st.json(cibil)
        st.write("**Agent 2:** Loan Decision Agent")
        st.json({
            "decision": result["final_decision"],
            "emi": result["emi"],
            "emi_ratio": result["loan_result"]["emi_ratio"],
            "reason": result["reason"],
        })
        st.write("**Sandbox:** Docker container `loan-calculation-sandbox` with `--network none`, CPU and memory limits, and `--rm` cleanup.")
