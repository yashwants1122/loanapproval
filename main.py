from typing import TypedDict
import json
import subprocess
from pathlib import Path

from langgraph.graph import StateGraph, START, END

DATA_FILE = Path(__file__).parent / "app" / "sample_customer.json"


class LoanState(TypedDict, total=False):
    customer: dict
    cibil_result: dict
    loan_result: dict
    emi: float
    final_decision: str
    reason: str


def cibil_agent(state: LoanState) -> LoanState:
    """Agent 1: assess the customer's credit profile."""
    customer = state["customer"]
    score = customer["cibil_score"]
    defaults = customer["payment_defaults"]
    active_loans = customer["active_loans"]

    if score >= 750 and defaults == 0:
        status = "GOOD"
    elif score >= 700 and defaults == 0:
        status = "ACCEPTABLE"
    else:
        status = "HIGH_RISK"

    return {
        **state,
        "cibil_result": {
            "score": score,
            "status": status,
            "active_loans": active_loans,
            "payment_defaults": defaults,
        },
    }


def run_sandbox(principal: float, annual_rate: float, months: int) -> float:
    """Run a fixed calculation inside the Docker sandbox."""
    payload = json.dumps({
        "principal": principal,
        "annual_rate": annual_rate,
        "months": months,
    })

    result = subprocess.run(
        [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", "128m",
            "--cpus", "0.25",
            "--read-only",
            "loan-calculation-sandbox",
            payload,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Sandbox failed: {result.stderr.strip()}")

    output = json.loads(result.stdout)
    return float(output["emi"])


def loan_decision_agent(state: LoanState) -> LoanState:
    """Agent 2: evaluate loan request and use sandbox for EMI calculation."""
    customer = state["customer"]
    cibil = state["cibil_result"]

    amount = customer["requested_amount"]
    salary = customer["monthly_salary"]
    rate = customer["annual_interest_rate"]
    months = customer["tenure_months"]

    # POC business rule.
    # Keep the sandbox responsible only for calculation, not the approval policy.
    emi = run_sandbox(amount, rate, months)
    emi_ratio = emi / salary

    if cibil["status"] in {"GOOD", "ACCEPTABLE"} and emi_ratio <= 0.40:
        decision = "APPROVED"
        reason = f"CIBIL is {cibil['status']} and EMI is {emi_ratio:.1%} of monthly salary."
    else:
        decision = "REJECTED"
        reason = f"Credit/affordability criteria not met. EMI is {emi_ratio:.1%} of monthly salary."

    return {
        **state,
        "emi": round(emi, 2),
        "loan_result": {"emi_ratio": round(emi_ratio, 4)},
        "final_decision": decision,
        "reason": reason,
    }


def build_graph():
    graph = StateGraph(LoanState)
    graph.add_node("cibil_agent", cibil_agent)
    graph.add_node("loan_decision_agent", loan_decision_agent)

    graph.add_edge(START, "cibil_agent")
    graph.add_edge("cibil_agent", "loan_decision_agent")
    graph.add_edge("loan_decision_agent", END)

    return graph.compile()


if __name__ == "__main__":
    customer = json.loads(DATA_FILE.read_text())
    app = build_graph()
    result = app.invoke({"customer": customer})

    print("\n===== LOAN APPROVAL POC =====")
    print(f"CIBIL Score : {result['cibil_result']['score']}")
    print(f"CIBIL Status: {result['cibil_result']['status']}")
    print(f"Loan Amount : ₹{customer['requested_amount']:,.0f}")
    print(f"EMI         : ₹{result['emi']:,.2f}")
    print(f"Decision    : {result['final_decision']}")
    print(f"Reason      : {result['reason']}")
