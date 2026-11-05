from pathlib import Path
import sys
import tempfile

from flow_report import FlowReport
from http_client import send_http_request
from stack_commands import (
    StackCommandFailedError,
    build_stack_environment,
    destroy_stack,
    find_free_local_port,
    start_stack,
    write_stack_environment_file,
)

EXPECTED_HEALTH_BODY = b'{"status":"ok"}'


def check_health(flow_report: FlowReport, *, api_publish_port: int) -> None:
    health_reply = send_http_request("/health", api_publish_port=api_publish_port, method="GET", headers={}, body=None)
    flow_report.record_check(
        "health",
        passed=health_reply.status == 200 and health_reply.body == EXPECTED_HEALTH_BODY,
        detail=f"{health_reply.status} {health_reply.body!r}",
    )


def run_health_flow() -> bool:
    flow_report = FlowReport()
    api_publish_port = find_free_local_port()
    with tempfile.TemporaryDirectory() as environment_directory:
        environment_file = write_stack_environment_file(Path(environment_directory), api_publish_port=api_publish_port)
        stack_environment = build_stack_environment(environment_file)
        try:
            start_stack(stack_environment)
            check_health(flow_report, api_publish_port=api_publish_port)
        except StackCommandFailedError as stack_error:
            flow_report.record_check("stack", passed=False, detail=str(stack_error))
        finally:
            destroy_stack(stack_environment)
    return flow_report.has_passed()


if __name__ == "__main__":
    sys.exit(0 if run_health_flow() else 1)
