-- Purpose: upgrade the existing question bank to the multi-language judge pool.
-- Compatibility: keeps authored Java starters; adds real cpp/python/go starters for the
--   seeded demo questions, neutralizes the broken legacy main_fuc splice, and normalizes
--   answer_config_json to declare all judge-pool languages.
-- Lock risk: full-table UPDATEs on tb_question (small table); run outside active exams.
-- Rollback: see rollback_V2026092301__question_bank_multilang.sql.

-- 1. Demo questions 20001-20005 ship a complete Java program as default_code while the
--    generic backfill left cpp/python/go as TODO skeletons. Give them equivalent,
--    runnable programs so every language tab matches the Java starter.
UPDATE tb_question
SET starter_code_json = JSON_OBJECT(
    'java', default_code,
    'cpp', '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    int a, b;\n    cin >> a >> b;\n    cout << a + b << endl;\n    return 0;\n}',
    'python', 'a, b = map(int, input().split())\nprint(a + b)',
    'go', 'package main\n\nimport "fmt"\n\nfunc main() {\n    var a, b int\n    _, _ = fmt.Scan(&a, &b)\n    fmt.Println(a + b)\n}'
)
WHERE question_type = 'PROGRAMMING'
  AND title = 'Two Sum A Plus B'
  AND default_code LIKE '%Scanner in = new Scanner(System.in)%'
  AND default_code LIKE '%a + b%';

UPDATE tb_question
SET starter_code_json = JSON_OBJECT(
    'java', default_code,
    'cpp', '#include <bits/stdc++.h>\nusing namespace std;\n\nbool isValid(const string& s) {\n    stack<char> st;\n    for (char c : s) {\n        if (c == ''('' || c == ''['' || c == ''{'') st.push(c);\n        else {\n            if (st.empty()) return false;\n            char top = st.top();\n            st.pop();\n            if ((c == '')'' && top != ''('') || (c == '']'' && top != ''['') || (c == ''}'' && top != ''{'')) return false;\n        }\n    }\n    return st.empty();\n}\n\nint main() {\n    string s;\n    getline(cin, s);\n    cout << (isValid(s) ? "true" : "false") << endl;\n    return 0;\n}',
    'python', 'def is_valid(s: str) -> bool:\n    stack = []\n    pairs = {'')'': ''('', '']'': ''['', ''}'': ''{''}\n    for c in s:\n        if c in ''([{'' :\n            stack.append(c)\n        elif not stack or stack.pop() != pairs[c]:\n            return False\n    return not stack\n\n\ns = input()\nprint(''true'' if is_valid(s) else ''false'')',
    'go', 'package main\n\nimport (\n    "bufio"\n    "fmt"\n    "os"\n)\n\nfunc isValid(s string) bool {\n    var stack []rune\n    pairs := map[rune]rune{'')'': ''('', '']'': ''['', ''}'': ''{''}\n    for _, c := range s {\n        if c == ''('' || c == ''['' || c == ''{'' {\n            stack = append(stack, c)\n            continue\n        }\n        if len(stack) == 0 || stack[len(stack)-1] != pairs[c] {\n            return false\n        }\n        stack = stack[:len(stack)-1]\n    }\n    return len(stack) == 0\n}\n\nfunc main() {\n    in := bufio.NewReader(os.Stdin)\n    out := bufio.NewWriter(os.Stdout)\n    defer out.Flush()\n    var line string\n    _, _ = fmt.Fscan(in, &line)\n    if isValid(line) {\n        fmt.Fprintln(out, "true")\n    } else {\n        fmt.Fprintln(out, "false")\n    }\n}'
)
WHERE question_type = 'PROGRAMMING'
  AND title = 'Valid Parentheses';

UPDATE tb_question
SET starter_code_json = JSON_OBJECT(
    'java', default_code,
    'cpp', '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    int n;\n    cin >> n;\n    vector<int> nums(n);\n    for (int i = 0; i < n; i++) cin >> nums[i];\n    int target;\n    cin >> target;\n    int left = 0, right = n - 1, ans = -1;\n    while (left <= right) {\n        int mid = left + (right - left) / 2;\n        if (nums[mid] == target) { ans = mid; break; }\n        if (nums[mid] < target) left = mid + 1; else right = mid - 1;\n    }\n    cout << ans << endl;\n    return 0;\n}',
    'python', 'def main():\n    n = int(input())\n    nums = list(map(int, input().split()))\n    target = int(input())\n    left, right, ans = 0, n - 1, -1\n    while left <= right:\n        mid = (left + right) // 2\n        if nums[mid] == target:\n            ans = mid\n            break\n        if nums[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    print(ans)\n\n\nmain()',
    'go', 'package main\n\nimport (\n    "bufio"\n    "fmt"\n    "os"\n)\n\nfunc main() {\n    in := bufio.NewReader(os.Stdin)\n    out := bufio.NewWriter(os.Stdout)\n    defer out.Flush()\n    var n int\n    _, _ = fmt.Fscan(in, &n)\n    nums := make([]int, n)\n    for i := 0; i < n; i++ {\n        _, _ = fmt.Fscan(in, &nums[i])\n    }\n    var target int\n    _, _ = fmt.Fscan(in, &target)\n    left, right, ans := 0, n-1, -1\n    for left <= right {\n        mid := left + (right-left)/2\n        if nums[mid] == target {\n            ans = mid\n            break\n        }\n        if nums[mid] < target {\n            left = mid + 1\n        } else {\n            right = mid - 1\n        }\n    }\n    fmt.Fprintln(out, ans)\n}'
)
WHERE question_type = 'PROGRAMMING'
  AND title = 'Binary Search';

UPDATE tb_question
SET starter_code_json = JSON_OBJECT(
    'java', default_code,
    'cpp', '#include <bits/stdc++.h>\nusing namespace std;\n\nint dx[] = {1, -1, 0, 0};\nint dy[] = {0, 0, 1, -1};\n\nvoid dfs(vector<string>& g, int x, int y) {\n    if (x < 0 || y < 0 || x >= (int)g.size() || y >= (int)g[0].size() || g[x][y] != ''1'') return;\n    g[x][y] = ''0'';\n    for (int k = 0; k < 4; k++) dfs(g, x + dx[k], y + dy[k]);\n}\n\nint main() {\n    int n, m;\n    cin >> n >> m;\n    vector<string> grid(n);\n    for (int i = 0; i < n; i++) cin >> grid[i];\n    int count = 0;\n    for (int i = 0; i < n; i++) {\n        for (int j = 0; j < m; j++) {\n            if (grid[i][j] == ''1'') {\n                count++;\n                dfs(grid, i, j);\n            }\n        }\n    }\n    cout << count << endl;\n    return 0;\n}',
    'python', 'import sys\n\n\ndef count_islands(grid, n, m):\n    count = 0\n    for i in range(n):\n        for j in range(m):\n            if grid[i][j] == ''1'':\n                count += 1\n                stack = [(i, j)]\n                grid[i][j] = ''0''\n                while stack:\n                    x, y = stack.pop()\n                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):\n                        if 0 <= nx < n and 0 <= ny < m and grid[nx][ny] == ''1'':\n                            grid[nx][ny] = ''0''\n                            stack.append((nx, ny))\n    return count\n\n\ndef main():\n    data = sys.stdin.read().split()\n    n, m = int(data[0]), int(data[1])\n    grid = [list(data[2 + i]) for i in range(n)]\n    print(count_islands(grid, n, m))\n\n\nmain()',
    'go', 'package main\n\nimport (\n    "bufio"\n    "fmt"\n    "os"\n)\n\nvar dx = [4]int{1, -1, 0, 0}\nvar dy = [4]int{0, 0, 1, -1}\n\nfunc dfs(g [][]byte, x, y int) {\n    if x < 0 || y < 0 || x >= len(g) || y >= len(g[0]) || g[x][y] != ''1'' {\n        return\n    }\n    g[x][y] = ''0''\n    for k := 0; k < 4; k++ {\n        dfs(g, x+dx[k], y+dy[k])\n    }\n}\n\nfunc main() {\n    in := bufio.NewReader(os.Stdin)\n    out := bufio.NewWriter(os.Stdout)\n    defer out.Flush()\n    var n, m int\n    _, _ = fmt.Fscan(in, &n, &m)\n    g := make([][]byte, n)\n    for i := 0; i < n; i++ {\n        var row string\n        _, _ = fmt.Fscan(in, &row)\n        g[i] = []byte(row)\n    }\n    count := 0\n    for i := 0; i < n; i++ {\n        for j := 0; j < m; j++ {\n            if g[i][j] == ''1'' {\n                count++\n                dfs(g, i, j)\n            }\n        }\n    }\n    fmt.Fprintln(out, count)\n}'
)
WHERE question_type = 'PROGRAMMING'
  AND title = 'Number of Islands';

UPDATE tb_question
SET starter_code_json = JSON_OBJECT(
    'java', default_code,
    'cpp', '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    int n;\n    cin >> n;\n    vector<int> tails(n);\n    int size = 0;\n    for (int i = 0; i < n; i++) {\n        int x;\n        cin >> x;\n        int l = 0, r = size;\n        while (l < r) {\n            int mid = (l + r) / 2;\n            if (tails[mid] < x) l = mid + 1; else r = mid;\n        }\n        tails[l] = x;\n        if (l == size) size++;\n    }\n    cout << size << endl;\n    return 0;\n}',
    'python', 'import bisect\n\n\ndef main():\n    n = int(input())\n    nums = list(map(int, input().split()))\n    tails = []\n    for x in nums:\n        pos = bisect.bisect_left(tails, x)\n        if pos == len(tails):\n            tails.append(x)\n        else:\n            tails[pos] = x\n    print(len(tails))\n\n\nmain()',
    'go', 'package main\n\nimport (\n    "bufio"\n    "fmt"\n    "os"\n)\n\nfunc main() {\n    in := bufio.NewReader(os.Stdin)\n    out := bufio.NewWriter(os.Stdout)\n    defer out.Flush()\n    var n int\n    _, _ = fmt.Fscan(in, &n)\n    tails := make([]int, 0, n)\n    for i := 0; i < n; i++ {\n        var x int\n        _, _ = fmt.Fscan(in, &x)\n        l, r := 0, len(tails)\n        for l < r {\n            mid := (l + r) / 2\n            if tails[mid] < x {\n                l = mid + 1\n            } else {\n                r = mid\n            }\n        }\n        if l == len(tails) {\n            tails = append(tails, x)\n        } else {\n            tails[l] = x\n        }\n    }\n    fmt.Fprintln(out, len(tails))\n}'
)
WHERE question_type = 'PROGRAMMING'
  AND title = 'Longest Increasing Subsequence';

-- 2. The legacy main_fuc splice is Java-only and the seeded value is a bare method
--    signature without a body, which corrupts Java submissions when appended.
UPDATE tb_question
SET main_fuc = NULL
WHERE main_fuc = 'public static void main(String[] args)';

-- 3. Declare the judge-pool languages on answer_config_json so the bank metadata
--    matches what the sandbox actually accepts.
UPDATE tb_question
SET answer_config_json = JSON_OBJECT(
    'languages', JSON_ARRAY('java', 'cpp', 'python', 'go'),
    'entry', 'stdin-stdout'
)
WHERE question_type = 'PROGRAMMING'
  AND answer_config_json IS NULL;

UPDATE tb_question
SET answer_config_json = JSON_SET(
    answer_config_json,
    '$.languages', JSON_ARRAY('java', 'cpp', 'python', 'go')
)
WHERE question_type = 'PROGRAMMING'
  AND JSON_EXTRACT(answer_config_json, '$.language') = 'java';

UPDATE tb_question
SET grading_config_json = JSON_OBJECT('mode', 'STANDARD')
WHERE question_type = 'PROGRAMMING'
  AND grading_config_json IS NULL;
