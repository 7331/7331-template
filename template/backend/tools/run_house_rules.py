import resource
import subprocess
import sys

from pydantic import BaseModel, ConfigDict, Field, JsonValue

SEMGREP_COMMAND = (
    "uvx",
    "semgrep==1.183.0",
    "scan",
    "--config",
    "semgrep/house-rules.yaml",
    "--metrics=off",
    "--strict",
    "--quiet",
    "--timeout",
    "60",
    "--json",
    "app",
    "migrations",
)
SEMGREP_TIMEOUT_SECONDS = 600
MESSAGE_PREVIEW_LENGTH = 200


class SemgrepPosition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    line: int


class SemgrepFindingExtra(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str = ""


class SemgrepFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")

    check_id: str
    path: str
    start: SemgrepPosition
    extra: SemgrepFindingExtra


class SemgrepError(BaseModel):
    model_config = ConfigDict(extra="ignore")

    error_type: JsonValue = Field(default="", validation_alias="type")
    path: str = ""
    message: JsonValue = ""


class SemgrepReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    results: list[SemgrepFinding]
    errors: list[SemgrepError]


def lift_stack_limit() -> None:
    _, hard_limit = resource.getrlimit(resource.RLIMIT_STACK)
    resource.setrlimit(resource.RLIMIT_STACK, (hard_limit, hard_limit))


def run_house_rules() -> SemgrepReport:
    lift_stack_limit()
    completed = subprocess.run(  # noqa: S603  # a fixed command, no outside input
        SEMGREP_COMMAND,
        capture_output=True,
        timeout=SEMGREP_TIMEOUT_SECONDS,
        check=False,
    )
    if not completed.stdout:
        sys.stderr.write(completed.stderr.decode(errors="replace"))
        raise SystemExit(completed.returncode or 1)
    return SemgrepReport.model_validate_json(completed.stdout)


def main() -> None:
    report = run_house_rules()
    for finding in report.results:
        print(
            f"{finding.path}:{finding.start.line} {finding.check_id}: {finding.extra.message[:MESSAGE_PREVIEW_LENGTH]}"
        )
    for error in report.errors:
        print(
            f"semgrep {str(error.error_type)[:MESSAGE_PREVIEW_LENGTH]} {error.path}: {str(error.message)[:MESSAGE_PREVIEW_LENGTH]}"
        )
    print(f"house rules: {len(report.results)} findings, {len(report.errors)} errors")
    sys.exit(1 if report.results or report.errors else 0)


if __name__ == "__main__":
    main()
