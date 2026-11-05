from pathlib import Path
import sys
import tempfile
import urllib.request

from stack_commands import (
    build_stack_environment,
    destroy_stack,
    find_free_local_port,
    start_stack,
    write_stack_environment_file,
)

REQUEST_TIMEOUT_SECONDS = 5
EXPECTED_HEALTH_BODY = b'{"status":"ok"}'


def read_health_body(api_publish_port: int) -> bytes:
    with urllib.request.urlopen(
        f"http://127.0.0.1:{api_publish_port}/health", timeout=REQUEST_TIMEOUT_SECONDS
    ) as response:
        return response.read()


def run_health_flow() -> bool:
    api_publish_port = find_free_local_port()
    with tempfile.TemporaryDirectory() as environment_directory:
        environment_file = write_stack_environment_file(Path(environment_directory), api_publish_port=api_publish_port)
        stack_environment = build_stack_environment(environment_file)
        try:
            start_stack(stack_environment)
            health_body = read_health_body(api_publish_port)
            passed = health_body == EXPECTED_HEALTH_BODY
            print(f"{'PASS' if passed else 'FAIL'} health: {health_body!r}", flush=True)
            return passed
        finally:
            destroy_stack(stack_environment)


if __name__ == "__main__":
    sys.exit(0 if run_health_flow() else 1)
