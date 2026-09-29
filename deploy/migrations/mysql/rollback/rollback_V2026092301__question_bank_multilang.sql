-- Logical rollback: restore the pre-migration shapes. Per-question starter_code_json
-- written by administrators after this migration cannot be restored automatically.
UPDATE tb_question
SET starter_code_json = JSON_OBJECT(
    'java', COALESCE(NULLIF(default_code, ''), 'import java.io.*;\npublic class Main {\n    public static void main(String[] args) throws Exception {\n        // TODO\n    }\n}'),
    'cpp', '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    // TODO\n    return 0;\n}',
    'python', 'import sys\n\ndef solve():\n    # TODO\n    pass\n\nif __name__ == "__main__":\n    solve()',
    'go', 'package main\n\nimport (\n    "bufio"\n    "fmt"\n    "os"\n)\n\nfunc main() {\n    in := bufio.NewReader(os.Stdin)\n    out := bufio.NewWriter(os.Stdout)\n    defer out.Flush()\n    _, _ = in, fmt.Fprint\n    // TODO\n}'
)
WHERE question_type = 'PROGRAMMING'
  AND title IN ('Two Sum A Plus B', 'Valid Parentheses', 'Binary Search',
                'Number of Islands', 'Longest Increasing Subsequence');

UPDATE tb_question
SET main_fuc = 'public static void main(String[] args)'
WHERE question_id IN (20001, 20002, 20003, 20004, 20005)
  AND main_fuc IS NULL;

UPDATE tb_question
SET answer_config_json = JSON_REMOVE(answer_config_json, '$.languages')
WHERE question_type = 'PROGRAMMING'
  AND JSON_EXTRACT(answer_config_json, '$.entry') = 'stdin-stdout'
  AND JSON_EXTRACT(answer_config_json, '$.sourceUrl') IS NOT NULL;

UPDATE tb_question
SET answer_config_json = NULL
WHERE question_type = 'PROGRAMMING'
  AND answer_config_json = JSON_OBJECT('languages', JSON_ARRAY('java', 'cpp', 'python', 'go'), 'entry', 'stdin-stdout');
