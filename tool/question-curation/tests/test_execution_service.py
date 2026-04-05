from app.services.execution_service import ExecutionService


def test_execution_service_returns_stdout_for_valid_java(settings, tmp_path) -> None:
    service = ExecutionService(settings)
    result = service.run_java_source(
        java_source="""
public class Solution {
    public static void main(String[] args) {
        System.out.print("ok");
    }
}
""".strip(),
        inputs=[],
        workdir=tmp_path,
    )

    assert result.exit_code == 0
    assert result.stdout == "ok"
