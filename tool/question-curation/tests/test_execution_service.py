from app.services.execution_service import ExecutionService
from app.services.generation_service import GenerationService


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


def test_execution_service_runs_packaged_function_style_problem(settings, tmp_path) -> None:
    generation_service = GenerationService()
    draft = generation_service.generate_from_statement(
        title="两数求和",
        statement_markdown="""
给定两个整数 a 和 b，请编写函数返回它们的和。

输入描述：
输入一行，包含两个整数 a 和 b，以空格分隔。

输出描述：
输出一个整数，表示 a + b 的结果。

样例输入
1 2

样例输出
3
""".strip(),
    )
    java_source = draft.default_code_java.replace("return 0;", "return a + b;")
    assembled = java_source.rsplit("}", 1)[0] + "\n\n" + draft.main_fuc_java + "\n}"

    service = ExecutionService(settings)
    result = service.run_java_source(
        java_source=assembled,
        inputs=["5 7"],
        workdir=tmp_path,
    )

    assert result.exit_code == 0
    assert result.stdout == "12"
