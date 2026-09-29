-- Add per-language starter programs while retaining default_code/main_fuc for legacy Java questions.
-- Idempotent: environments that received starter_code_json out-of-band (before Flyway tracked it)
-- skip the ALTER instead of failing on a duplicate column.
SET @starter_col_exists := (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'tb_question'
      AND column_name = 'starter_code_json'
);
SET @starter_ddl := IF(@starter_col_exists = 0,
    'ALTER TABLE tb_question ADD COLUMN starter_code_json json NULL AFTER default_code',
    'SELECT ''starter_code_json already present''');
PREPARE starter_stmt FROM @starter_ddl;
EXECUTE starter_stmt;
DEALLOCATE PREPARE starter_stmt;

UPDATE tb_question
SET starter_code_json = JSON_OBJECT(
    'java', COALESCE(NULLIF(default_code, ''), 'import java.io.*;\npublic class Main {\n    public static void main(String[] args) throws Exception {\n        // TODO\n    }\n}'),
    'cpp', '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    // TODO\n    return 0;\n}',
    'python', 'import sys\n\ndef solve():\n    # TODO\n    pass\n\nif __name__ == "__main__":\n    solve()',
    'go', 'package main\n\nimport (\n    "bufio"\n    "fmt"\n    "os"\n)\n\nfunc main() {\n    in := bufio.NewReader(os.Stdin)\n    out := bufio.NewWriter(os.Stdout)\n    defer out.Flush()\n    _, _ = in, fmt.Fprint\n    // TODO\n}'
)
WHERE question_type = 'PROGRAMMING'
  AND starter_code_json IS NULL;
