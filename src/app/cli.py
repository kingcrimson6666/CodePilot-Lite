from __future__ import annotations

import json
from pathlib import Path
import time
import re

import typer
from rich.console import Console
from rich import print
from rich.table import Table

from src.app.bootstrap import build_orchestrator
from src.governance.convergence import evaluate_release_gate
from src.governance.approval_gate import ApprovalGate
from src.infra.config import AppSettings
from src.observability.metrics_db import (
    build_trend_snapshot,
    detect_tsr_drift,
    read_latest_eval_summary,
    read_recent_eval_summaries,
    write_eval_summary,
)
from src.rag.factory import build_rag_store, ensure_rag_dirs
from src.rag.indexer import RAGIndexer

app = typer.Typer(help="CodePilot Lite CLI")
console = Console()

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
except Exception:  # noqa: BLE001
    PromptSession = None
    InMemoryHistory = None


def _interactive_confirm(tool_name: str, ticket_id: str, args: dict) -> bool:
    path_info = args.get("path", args.get("target_path", "unknown"))
    content_preview = ""
    if tool_name == "write_file" and "code" in args:
        code = args.get("code", "")
        lines = code.split("\n")[:5]
        content_preview = "\n".join(lines)
        if len(code.split("\n")) > 5:
            content_preview += "\n    ..."

    print("\n" + "=" * 50)
    print(f"[yellow]⚠️  高风险操作需要确认[/yellow]")
    print(f"工具: {tool_name}")
    print(f"票据ID: {ticket_id}")
    if path_info != "unknown":
        print(f"目标路径: {path_info}")
    if content_preview:
        print("代码预览:")
        print(content_preview)
    print("=" * 50)

    while True:
        try:
            choice = input("是否允许执行? (y/n): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n已拒绝")
            return False

        if choice in ("y", "yes", "是", "1"):
            return True
        if choice in ("n", "no", "否", "0"):
            return False
        print("请输入 y (是) 或 n (否)")


def _parse_chat_mode_message(user_input: str) -> tuple[str, str]:
    text = user_input.strip()
    if text.startswith("/task "):
        return "task", text[len("/task "):].strip()
    if text.startswith("/任务 "):
        return "task", text[len("/任务 "):].strip()
    if text.startswith("/执行 "):
        return "task", text[len("/执行 "):].strip()
    if text.startswith("任务："):
        return "task", text[len("任务："):].strip()
    return "chat", text


def _looks_like_coding_task(text: str) -> bool:
    lowered = text.lower().strip()
    question_markers = (
        "吗",
        "么",
        "呢",
        "？",
        "?",
        "能不能",
        "可不可以",
        "是否",
        "是不是",
        "会不会",
        "你能",
        "你可以",
        "能否",
        "怎么",
        "为何",
        "为什么",
        "是什么",
    )

    task_markers = (
        "修复",
        "修改",
        "实现",
        "添加",
        "删除",
        "重构",
        "优化",
        "排查",
        "检查",
        "生成",
        "运行",
        "测试",
        "构建",
        "build-index",
        "build index",
        "run --task",
        "read_file",
        "write_file",
        "apply_patch",
        "search_code",
        "cli",
        "代码",
        "文件",
        "函数",
        "接口",
        "报错",
        "bug",
        "修bug",
        "怎么改",
        "怎么实现",
        "帮我",
        "请你",
        "新建",
        "创建",
        "写一个",
        "写代码",
    )

    has_question = any(marker in text for marker in question_markers)
    has_task = any(marker in text for marker in task_markers)

    if has_task:
        return True

    if re.search(r"\b(src|tests?|README|pyproject|setup|cli|orchestrator|prompt|rag|memory)\b", lowered):
        return True

    return False


def _print_task_result(result, *, raw_json: bool = False) -> None:
    if raw_json:
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        return

    print("[bold green]任务结果[/bold green]")
    print(f"任务：{result.task}")
    print(f"结论：{result.final_answer}")
    print(f"通过：{'是' if result.total_score.passed else '否'}")
    print(
        "评分："
        f"hard={result.total_score.hard:.3f}, "
        f"judge={result.total_score.judge:.3f}, "
        f"total={result.total_score.total:.3f}"
    )
    if result.tool_history:
        print("工具记录：")
        for item in result.tool_history:
            print(f"- {item}")
    if result.pending_approval_tickets:
        print("待审批：")
        for ticket in result.pending_approval_tickets:
            print(f"- {ticket}")
    if result.replay_path:
        print(f"回放文件：{result.replay_path}")


@app.command()
def run(
    task: str = typer.Option(..., help="Task instruction for the assistant"),
    raw_json: bool = typer.Option(False, "--raw-json/--no-raw-json", help="Print raw JSON result"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Ask for confirmation before high-risk operations"),
) -> None:
    confirm_fn = _interactive_confirm if interactive else None
    orchestrator = build_orchestrator(interactive_confirm=confirm_fn)
    result = orchestrator.run_task(task)
    _print_task_result(result, raw_json=raw_json)


@app.command("chat")
def chat(
    session: str | None = typer.Option(None, help="Session id to reuse (optional)"),
    stream: bool = typer.Option(False, "--stream/--no-stream", help="Use streaming LLM output"),
    auto_route: bool = typer.Option(True, "--auto-route/--no-auto-route", help="Auto-detect coding tasks in chat"),
    raw_json: bool = typer.Option(False, "--raw-json/--no-raw-json", help="Print raw JSON for task results"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Ask for confirmation before high-risk operations"),
) -> None:
    """Interactive chat REPL. 输入 `exit` 或 `quit` 结束会话。"""
    confirm_fn = _interactive_confirm if interactive else None
    orchestrator = build_orchestrator(interactive_confirm=confirm_fn)
    # reuse provided session id or generate one per process
    repl_session = session or "cli-chat"
    prompt_session = None
    if PromptSession is not None and InMemoryHistory is not None:
        prompt_session = PromptSession(history=InMemoryHistory())
    print(f"开始交互式会话，session={repl_session}. 输入 exit/quit 结束。")
    try:
        while True:
            if prompt_session is not None:
                user_input = prompt_session.prompt("你: ").strip()
            else:
                user_input = input("你: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("结束会话。")
                break
            mode, payload = _parse_chat_mode_message(user_input)
            if not payload:
                print("请输入内容。若要交给助手执行编程任务，可以使用 /task 你的任务描述")
                continue
            if mode == "task" or (auto_route and _looks_like_coding_task(payload)):
                result = orchestrator.run_task(payload, session_id=repl_session)
                _print_task_result(result, raw_json=raw_json)
                continue
            if stream:
                gateway = orchestrator.llm_gateway
                # load short memory context
                short_mem = orchestrator.short_memory
                ctx = short_mem.read(repl_session)
                short_mem.write(repl_session, f"USER: {payload}")
                print("[bold green]助手回复（流式）[/bold green]")
                assistant_buf = ""
                for chunk in gateway.stream_chat(payload, context=ctx):
                    print(chunk, end="", flush=True)
                    assistant_buf += chunk
                print("\n")
                short_mem.write(repl_session, f"ASSISTANT: {assistant_buf}")
            else:
                gateway = orchestrator.llm_gateway
                short_mem = orchestrator.short_memory
                ctx = short_mem.read(repl_session)
                short_mem.write(repl_session, f"USER: {payload}")
                chunks = []
                for chunk in gateway.stream_chat(payload, context=ctx):
                    chunks.append(chunk)
                assistant_text = "".join(chunks).strip()
                short_mem.write(repl_session, f"ASSISTANT: {assistant_text}")
                print("[bold green]助手回复[/bold green]")
                print(assistant_text)
    except (KeyboardInterrupt, EOFError):
        print("\n会话中断，退出。")


@app.command("build-index")
def build_index(repo: str = typer.Option(".", help="Repository path to index")) -> None:
    settings = AppSettings()
    ensure_rag_dirs(settings)
    store = build_rag_store(settings)
    indexer = RAGIndexer(store)
    count = indexer.build_index(repo)
    print(f"Indexed chunks: {count}")


@app.command()
def replay(path: str = typer.Option("data/replays/latest.json", help="Replay file path")) -> None:
    p = Path(path)
    if not p.exists():
        raise typer.BadParameter(f"Replay file not found: {path}")
    print(p.read_text(encoding="utf-8"))


@app.command("approvals-pending")
def approvals_pending(path: str | None = typer.Option(None, help="Approval log path")) -> None:
    settings = AppSettings()
    log_path = Path(path) if path else settings.approval_log_path
    gate = ApprovalGate(log_path=log_path, auto_approve_high_risk=settings.auto_approve_high_risk)
    pending = gate.list_pending()
    print(json.dumps(pending, ensure_ascii=False, indent=2))


@app.command("approve")
def approve(
    ticket_id: str = typer.Option(..., help="Approval ticket id"),
    actor: str = typer.Option("cli", help="Decision actor"),
    path: str | None = typer.Option(None, help="Approval log path"),
) -> None:
    settings = AppSettings()
    log_path = Path(path) if path else settings.approval_log_path
    gate = ApprovalGate(log_path=log_path, auto_approve_high_risk=settings.auto_approve_high_risk)
    decision = gate.decide(ticket_id=ticket_id, approve=True, actor=actor)
    print(json.dumps(decision.__dict__, ensure_ascii=False, indent=2))


@app.command("reject")
def reject(
    ticket_id: str = typer.Option(..., help="Approval ticket id"),
    actor: str = typer.Option("cli", help="Decision actor"),
    path: str | None = typer.Option(None, help="Approval log path"),
) -> None:
    settings = AppSettings()
    log_path = Path(path) if path else settings.approval_log_path
    gate = ApprovalGate(log_path=log_path, auto_approve_high_risk=settings.auto_approve_high_risk)
    decision = gate.decide(ticket_id=ticket_id, approve=False, actor=actor)
    print(json.dumps(decision.__dict__, ensure_ascii=False, indent=2))


@app.command("eval-run")
def eval_run(
    dataset: str = typer.Option(..., help="Path to jsonl dataset with {\"task\": ...}"),
    out: str = typer.Option("data/eval/reports/latest.json", help="Output report path"),
    max_retries: int = typer.Option(0, help="Retries after first attempt to recover failed tasks"),
) -> None:
    ds_path = Path(dataset)
    if not ds_path.exists():
        raise typer.BadParameter(f"Dataset not found: {dataset}")

    dataset_rows = [json.loads(line) for line in ds_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    orchestrator = build_orchestrator()

    reports = []
    durations = []
    passed = 0
    first_passed = 0
    failed_calls = 0
    total_calls = 0

    for row in dataset_rows:
        task = row["task"]
        started = time.perf_counter()
        result = orchestrator.run_task(task)
        payload = result.model_dump()

        if payload["total_score"]["passed"]:
            first_passed += 1

        attempt = 0
        while not payload["total_score"]["passed"] and attempt < max(0, max_retries):
            attempt += 1
            retry_result = orchestrator.run_task(task)
            payload = retry_result.model_dump()

        durations.append((time.perf_counter() - started) * 1000)
        reports.append(payload)
        if payload["total_score"]["passed"]:
            passed += 1
        history = payload.get("tool_history", [])
        total_calls += len(history)
        failed_calls += sum(1 for evt in history if "failed" in evt.lower())

    total = len(reports)
    output = {
        "summary": {
            "total_tasks": total,
            "passed_tasks": passed,
            "tsr": (passed / total) if total else 0.0,
            "otr": (first_passed / total) if total else 0.0,
            "mttr_ms": (sum(durations) / total) if total else 0.0,
            "invalid_tool_call_rate": (failed_calls / total_calls) if total_calls else 0.0,
        },
        "reports": reports,
    }

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    settings = AppSettings()
    write_eval_summary(summary=output["summary"], report_path=str(out_path), db_path=settings.metrics_db_path)
    print(f"Wrote report: {out_path}")


@app.command("eval-compare")
def eval_compare(
    run_a: str = typer.Option(..., help="Path of report A"),
    run_b: str = typer.Option(..., help="Path of report B"),
) -> None:
    payload_a = json.loads(Path(run_a).read_text(encoding="utf-8"))
    payload_b = json.loads(Path(run_b).read_text(encoding="utf-8"))

    reports_a = payload_a["reports"] if isinstance(payload_a, dict) and "reports" in payload_a else payload_a
    reports_b = payload_b["reports"] if isinstance(payload_b, dict) and "reports" in payload_b else payload_b

    avg_a = sum(item["total_score"]["total"] for item in reports_a) / len(reports_a) if reports_a else 0.0
    avg_b = sum(item["total_score"]["total"] for item in reports_b) / len(reports_b) if reports_b else 0.0

    print(json.dumps({"run_a_avg": avg_a, "run_b_avg": avg_b, "delta": avg_b - avg_a}, ensure_ascii=False, indent=2))


@app.command("convergence-check")
def convergence_check(
    limit: int = typer.Option(5, help="How many latest eval runs to inspect"),
    threshold: float = typer.Option(0.65, help="Minimum TSR threshold"),
    min_runs: int = typer.Option(2, help="Minimum recent runs for release decision"),
    max_drop: float = typer.Option(0.05, help="Maximum allowed TSR drop between recent runs"),
    db_path: str | None = typer.Option(None, help="Metrics DB path, defaults to app settings"),
) -> None:
    settings = AppSettings()
    path = Path(db_path) if db_path else settings.metrics_db_path
    rows = read_recent_eval_summaries(db_path=path, limit=limit)
    rates = [float(row.get("tsr", 0.0)) for row in reversed(rows)]
    decision = evaluate_release_gate(
        recent_success_rates=rates,
        threshold=threshold,
        min_runs=min_runs,
        max_drop=max_drop,
    )
    print(json.dumps({"decision": decision, "recent_tsr": rates}, ensure_ascii=False, indent=2))


@app.command("metrics-trend")
def metrics_trend(
    trend_window: int = typer.Option(5, help="Recent eval runs to aggregate"),
    baseline_window: int = typer.Option(5, help="Baseline window size for drift detection"),
    recent_window: int = typer.Option(3, help="Recent window size for drift detection"),
    tolerance: float = typer.Option(0.05, help="Allowed TSR drop before reporting drift"),
    db_path: str | None = typer.Option(None, help="Metrics DB path, defaults to app settings"),
) -> None:
    settings = AppSettings()
    path = Path(db_path) if db_path else settings.metrics_db_path
    trend = build_trend_snapshot(db_path=path, window=trend_window)
    drift = detect_tsr_drift(
        db_path=path,
        baseline_window=baseline_window,
        recent_window=recent_window,
        tolerance=tolerance,
    )
    print(json.dumps({"trend": trend, "drift": drift}, ensure_ascii=False, indent=2))


@app.command("metrics-dashboard")
def metrics_dashboard(
    limit: int = typer.Option(10, help="How many recent runs to show"),
    db_path: str | None = typer.Option(None, help="Metrics DB path, defaults to app settings"),
) -> None:
    settings = AppSettings()
    path = Path(db_path) if db_path else settings.metrics_db_path
    rows = read_recent_eval_summaries(db_path=path, limit=limit)

    table = Table(title="CodePilot Metrics Dashboard")
    table.add_column("created_at")
    table.add_column("tasks", justify="right")
    table.add_column("passed", justify="right")
    table.add_column("TSR", justify="right")
    table.add_column("OTR", justify="right")
    table.add_column("MTTR(ms)", justify="right")
    table.add_column("invalid_tool_rate", justify="right")

    for row in rows:
        table.add_row(
            str(row.get("created_at", "")),
            str(row.get("total_tasks", 0)),
            str(row.get("passed_tasks", 0)),
            f"{float(row.get('tsr', 0.0)):.3f}",
            f"{float(row.get('otr', 0.0)):.3f}",
            f"{float(row.get('mttr_ms', 0.0)):.1f}",
            f"{float(row.get('invalid_tool_call_rate', 0.0)):.3f}",
        )
    console.print(table)


@app.command("release-gate")
def release_gate(
    limit: int = typer.Option(8, help="How many recent eval runs to inspect"),
    threshold: float = typer.Option(0.65, help="Minimum TSR threshold"),
    min_runs: int = typer.Option(2, help="Minimum recent runs for convergence decision"),
    max_drop: float = typer.Option(0.05, help="Max allowed TSR drop for convergence"),
    baseline_window: int = typer.Option(5, help="Baseline window for drift check"),
    recent_window: int = typer.Option(3, help="Recent window for drift check"),
    drift_tolerance: float = typer.Option(0.05, help="Allowed TSR drop before drift alert"),
    min_latest_tasks: int = typer.Option(20, help="DoD minimum tasks in latest eval run"),
    strict: bool = typer.Option(False, help="Exit non-zero if gate does not pass"),
    db_path: str | None = typer.Option(None, help="Metrics DB path, defaults to app settings"),
) -> None:
    settings = AppSettings()
    path = Path(db_path) if db_path else settings.metrics_db_path

    rows = read_recent_eval_summaries(db_path=path, limit=limit)
    rates = [float(row.get("tsr", 0.0)) for row in reversed(rows)]
    convergence = evaluate_release_gate(
        recent_success_rates=rates,
        threshold=threshold,
        min_runs=min_runs,
        max_drop=max_drop,
    )
    drift = detect_tsr_drift(
        db_path=path,
        baseline_window=baseline_window,
        recent_window=recent_window,
        tolerance=drift_tolerance,
    )
    latest = read_latest_eval_summary(db_path=path)
    dod_tasks_ok = bool(latest) and int(latest.get("total_tasks", 0)) >= int(min_latest_tasks)

    decision = {
        "allowed": bool(convergence.get("allowed", False)) and (not bool(drift.get("drifted", False))) and dod_tasks_ok,
        "convergence": convergence,
        "drift": drift,
        "dod_latest_tasks_ok": dod_tasks_ok,
        "latest_total_tasks": int(latest.get("total_tasks", 0)) if latest else 0,
        "required_latest_tasks": int(min_latest_tasks),
    }
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    if strict and not decision["allowed"]:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
