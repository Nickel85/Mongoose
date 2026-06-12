"""Interactive session loop for the Njord agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TextIO

from terminal import style_output, styled


AgentCall = Callable[[], tuple[bool, str]]
AnswerCall = Callable[[str], tuple[bool, str]]


@dataclass(frozen=True)
class ResponseEvent:
    kind: str
    text: str = ""


RESPONSE_EVENT_KINDS = {
    "text",
    "warning",
    "error",
    "prompt",
    "approval_request",
    "done",
}
SESSION_COMMANDS = {
    "/help": "Show session commands.",
    "/status": "Check local Njord configuration without printing secrets.",
    "/brief": "Generate the read-only financial brief.",
    "/summary": "Generate the read-only YNAB budget summary.",
    "/spending": "Review current-month spending.",
    "/exit": "Exit the Njord session.",
    "/quit": "Exit the Njord session.",
}
EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit"}
PROMPT = "Njord> "


def help_text() -> str:
    lines = ["Njord session commands"]
    lines.extend(f"- {command}: {description}" for command, description in SESSION_COMMANDS.items())
    lines.extend(
        [
            "",
            "Type a budget, spending, configuration, or brief request to route it through Njord.",
            "Budget-changing requests are read-only for now and cannot mutate YNAB from chat.",
        ]
    )
    return "\n".join(lines)


def response_events(ok: bool, output: str) -> list[ResponseEvent]:
    if ok:
        return [ResponseEvent("text", output), ResponseEvent("done")]
    return [ResponseEvent("error", output), ResponseEvent("done")]


def handle_input(
    raw_input: str,
    *,
    answer_request: AnswerCall,
    config_status: AgentCall,
    brief: AgentCall,
    budget_summary: AgentCall,
    spending_review: AgentCall,
) -> tuple[bool, list[ResponseEvent]]:
    request = raw_input.strip()
    if not request:
        return False, []

    normalized = request.lower()
    if normalized in EXIT_COMMANDS:
        return True, [ResponseEvent("done")]

    if request.startswith("/"):
        if normalized == "/help":
            return False, [ResponseEvent("text", help_text()), ResponseEvent("done")]
        if normalized == "/status":
            return False, response_events(*config_status())
        if normalized == "/brief":
            return False, response_events(*brief())
        if normalized == "/summary":
            return False, response_events(*budget_summary())
        if normalized == "/spending":
            return False, response_events(*spending_review())
        return False, [
            ResponseEvent("warning", f"Unknown session command: {request}\nRun /help to see available commands."),
            ResponseEvent("done"),
        ]

    return False, response_events(*answer_request(request))


def render_event(event: ResponseEvent, *, color_enabled: bool, output_stream: TextIO) -> None:
    if event.kind not in RESPONSE_EVENT_KINDS:
        raise ValueError(f"Unknown response event kind: {event.kind}")

    if event.kind == "done" or not event.text:
        return

    if event.kind == "prompt":
        rendered = styled(event.text, "selected", color_enabled)
        output_stream.write(rendered)
        output_stream.flush()
        return

    if event.kind == "warning":
        rendered = styled(event.text, "warning", color_enabled)
    elif event.kind == "error":
        rendered = styled(style_output(event.text, color_enabled), "error", color_enabled)
    elif event.kind == "approval_request":
        rendered = styled(style_output(event.text, color_enabled), "warning", color_enabled)
    else:
        rendered = style_output(event.text, color_enabled)
    output_stream.write(f"{rendered}\n")


def run_repl(
    *,
    input_stream: TextIO,
    output_stream: TextIO,
    color_enabled: bool,
    answer_request: AnswerCall,
    config_status: AgentCall,
    brief: AgentCall,
    budget_summary: AgentCall,
    spending_review: AgentCall,
) -> int:
    while True:
        render_event(ResponseEvent("prompt", PROMPT), color_enabled=color_enabled, output_stream=output_stream)
        raw_input = input_stream.readline()
        if raw_input == "":
            output_stream.write("\n")
            return 0

        should_exit, events = handle_input(
            raw_input,
            answer_request=answer_request,
            config_status=config_status,
            brief=brief,
            budget_summary=budget_summary,
            spending_review=spending_review,
        )
        for event in events:
            render_event(event, color_enabled=color_enabled, output_stream=output_stream)
        if should_exit:
            return 0
