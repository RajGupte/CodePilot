"""LangGraph supervisor: routes incoming events (issues vs. PR diffs) to the
correct agent and returns a unified result.

This is intentionally the simplest possible graph shape — one router node,
two worker nodes — since both agents are already proven correct in isolation.
Complexity (retries, human-approval gating, multi-step chains) gets added
incrementally on top of this working skeleton, not before it.
"""

from typing import Literal, TypedDict, Optional

from langgraph.graph import StateGraph, END

from app.agents.triage import triage_issue
from app.agents.review import review_diff
from app.agents.schemas import TriageResult, ReviewResult
from app.agents.gate import submit_for_approval


class GraphState(TypedDict):
    event_type: Literal["issue", "pr_diff"]
    repo_name: str
    # issue inputs
    title: Optional[str]
    body: Optional[str]
    # pr_diff inputs
    diff: Optional[str]
    # outputs
    triage_result: Optional[TriageResult]
    review_result: Optional[ReviewResult]


def route_event(state: GraphState) -> Literal["triage_node", "review_node"]:
    """Decide which agent handles this event."""
    if state["event_type"] == "issue":
        return "triage_node"
    return "review_node"


def triage_node(state: GraphState) -> dict:
    result = triage_issue(
        title=state["title"],
        body=state["body"],
        repo_name=state["repo_name"],
    )
    submit_for_approval(
        repo_name=state["repo_name"],
        action_type="triage",
        agent_output=result.model_dump(),
        source_title=state["title"],
        source_body=state["body"],
    )
    return {"triage_result": result}


def review_node(state: GraphState) -> dict:
    result = review_diff(
        diff=state["diff"],
        repo_name=state["repo_name"],
    )
    submit_for_approval(
        repo_name=state["repo_name"],
        action_type="review",
        agent_output=result.model_dump(),
        source_diff=state["diff"],
    )
    return {"review_result": result}


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("triage_node", triage_node)
    graph.add_node("review_node", review_node)

    graph.set_conditional_entry_point(
        route_event,
        {
            "triage_node": "triage_node",
            "review_node": "review_node",
        },
    )

    graph.add_edge("triage_node", END)
    graph.add_edge("review_node", END)

    return graph.compile()


codepilot_graph = build_graph()
