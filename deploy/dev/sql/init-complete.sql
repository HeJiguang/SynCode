-- Unified development database bootstrap for OnlineOJ / SynCode.
-- Target database: bitoj_dev
-- One-pass schema + demo seed data for local code + cloud middleware testing.

USE bitoj_dev;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS tb_sys_user (
    user_id bigint unsigned NOT NULL COMMENT 'system user id',
    user_account varchar(20) NOT NULL COMMENT 'login account',
    nick_name varchar(20) DEFAULT NULL COMMENT 'display name',
    password char(60) NOT NULL COMMENT 'bcrypt password',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (user_id),
    UNIQUE KEY idx_user_account (user_account)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='backend admin users';

CREATE TABLE IF NOT EXISTS tb_question (
    question_id bigint unsigned NOT NULL COMMENT 'question id',
    title varchar(50) NOT NULL COMMENT 'question title',
    difficulty tinyint NOT NULL COMMENT '1 easy 2 medium 3 hard',
    algorithm_tag varchar(100) DEFAULT NULL COMMENT 'primary algorithm tag',
    knowledge_tags varchar(500) DEFAULT NULL COMMENT 'comma separated tags',
    estimated_minutes int DEFAULT NULL COMMENT 'estimated solving time',
    training_enabled tinyint NOT NULL DEFAULT 1 COMMENT 'whether training can use this question',
    time_limit int NOT NULL COMMENT 'time limit ms',
    space_limit int NOT NULL COMMENT 'space limit kb',
    content varchar(1000) NOT NULL COMMENT 'problem statement',
    question_case varchar(1000) DEFAULT NULL COMMENT 'json cases',
    default_code varchar(2000) NOT NULL COMMENT 'starter code',
    main_fuc varchar(500) NOT NULL COMMENT 'entry code block',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='problem bank';

CREATE TABLE IF NOT EXISTS tb_exam (
    exam_id bigint unsigned NOT NULL COMMENT 'exam id',
    title varchar(50) NOT NULL COMMENT 'exam title',
    start_time datetime NOT NULL COMMENT 'start time',
    end_time datetime NOT NULL COMMENT 'end time',
    status tinyint NOT NULL DEFAULT 0 COMMENT '0 draft 1 published',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (exam_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='exam header';

CREATE TABLE IF NOT EXISTS tb_exam_question (
    exam_question_id bigint unsigned NOT NULL COMMENT 'exam question relation id',
    question_id bigint unsigned NOT NULL COMMENT 'question id',
    exam_id bigint unsigned NOT NULL COMMENT 'exam id',
    question_order int NOT NULL COMMENT 'display order',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (exam_question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='exam question relation';

CREATE TABLE IF NOT EXISTS tb_user (
    user_id bigint unsigned NOT NULL COMMENT 'user id',
    nick_name varchar(20) DEFAULT NULL COMMENT 'nickname',
    head_image varchar(200) DEFAULT NULL COMMENT 'avatar',
    sex tinyint DEFAULT NULL COMMENT '1 male 2 female',
    phone varchar(20) DEFAULT NULL COMMENT 'optional phone after email-login pivot',
    code char(6) DEFAULT NULL COMMENT 'email verification code',
    email varchar(100) DEFAULT NULL COMMENT 'email used by email-code login',
    wechat varchar(20) DEFAULT NULL COMMENT 'wechat id',
    school_name varchar(50) DEFAULT NULL COMMENT 'school',
    major_name varchar(50) DEFAULT NULL COMMENT 'major',
    introduce varchar(255) DEFAULT NULL COMMENT 'bio',
    status tinyint NOT NULL COMMENT '0 blocked 1 normal',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='frontend users';

CREATE TABLE IF NOT EXISTS tb_user_exam (
    user_exam_id bigint unsigned NOT NULL COMMENT 'user exam relation id',
    user_id bigint unsigned NOT NULL COMMENT 'user id',
    exam_id bigint unsigned NOT NULL COMMENT 'exam id',
    score int unsigned DEFAULT NULL COMMENT 'score',
    exam_rank int unsigned DEFAULT NULL COMMENT 'rank',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (user_exam_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='user exam relation';

CREATE TABLE IF NOT EXISTS tb_user_submit (
    submit_id bigint unsigned NOT NULL COMMENT 'submit id',
    request_id varchar(64) NOT NULL COMMENT 'async judge request id',
    user_id bigint unsigned NOT NULL COMMENT 'user id',
    question_id bigint unsigned NOT NULL COMMENT 'question id',
    exam_id bigint unsigned DEFAULT NULL COMMENT 'exam id',
    program_type tinyint NOT NULL COMMENT '0 java 1 cpp',
    user_code text NOT NULL COMMENT 'submitted code',
    pass tinyint NOT NULL COMMENT '0 failed 1 passed 2 not submitted 3 judging',
    exe_message varchar(500) NOT NULL COMMENT 'execution message',
    score int NOT NULL DEFAULT 0 COMMENT 'score',
    case_judge_res text DEFAULT NULL COMMENT 'case result json',
    use_time bigint DEFAULT NULL COMMENT 'runtime ms',
    use_memory bigint DEFAULT NULL COMMENT 'memory kb',
    judge_status tinyint NOT NULL DEFAULT 0 COMMENT '0 waiting 1 success 2 dead-letter 3 publish-failed',
    retry_count int NOT NULL DEFAULT 0 COMMENT 'retry count snapshot',
    last_error varchar(1000) DEFAULT NULL COMMENT 'last error summary',
    finish_time datetime DEFAULT NULL COMMENT 'finished time',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (submit_id),
    UNIQUE KEY uk_request_id (request_id),
    KEY idx_user_question_exam_create (user_id, question_id, exam_id, create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='user submit history';

CREATE TABLE IF NOT EXISTS tb_message_text (
    text_id bigint unsigned NOT NULL COMMENT 'message content id',
    message_title varchar(50) NOT NULL COMMENT 'message title',
    message_content varchar(500) NOT NULL COMMENT 'message content',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (text_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='message content';

CREATE TABLE IF NOT EXISTS tb_message (
    message_id bigint unsigned NOT NULL COMMENT 'message id',
    text_id bigint unsigned NOT NULL COMMENT 'message content id',
    send_id bigint unsigned NOT NULL COMMENT 'sender id',
    rec_id bigint unsigned NOT NULL COMMENT 'receiver id',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='message relation';

CREATE TABLE IF NOT EXISTS tb_notice (
    notice_id bigint unsigned NOT NULL COMMENT 'notice id',
    title varchar(100) NOT NULL COMMENT 'notice title',
    content text NOT NULL COMMENT 'notice content',
    category varchar(32) NOT NULL DEFAULT 'Announcement' COMMENT 'notice category',
    is_public tinyint NOT NULL DEFAULT 1 COMMENT '0 private 1 public',
    is_pinned tinyint NOT NULL DEFAULT 0 COMMENT '0 normal 1 pinned',
    status tinyint NOT NULL DEFAULT 0 COMMENT '0 draft 1 published',
    publish_time datetime DEFAULT NULL COMMENT 'publish time',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (notice_id),
    KEY idx_notice_public_publish (is_public, status, publish_time),
    KEY idx_notice_pinned_publish (is_pinned, publish_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='system notice';

CREATE TABLE IF NOT EXISTS tb_training_profile (
    profile_id bigint unsigned NOT NULL COMMENT 'training profile id',
    user_id bigint unsigned NOT NULL COMMENT 'user id',
    current_level varchar(32) DEFAULT NULL COMMENT 'current level',
    target_direction varchar(100) DEFAULT NULL COMMENT 'target direction',
    weak_points text COMMENT 'weak points summary',
    strong_points text COMMENT 'strong points summary',
    last_test_exam_id bigint unsigned DEFAULT NULL COMMENT 'last test exam id',
    last_plan_id bigint unsigned DEFAULT NULL COMMENT 'last plan id',
    status tinyint NOT NULL DEFAULT 1 COMMENT '0 disabled 1 enabled',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (profile_id),
    UNIQUE KEY uk_training_profile_user_id (user_id),
    KEY idx_training_profile_last_plan_id (last_plan_id),
    KEY idx_training_profile_last_test_exam_id (last_test_exam_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='training profile';

CREATE TABLE IF NOT EXISTS tb_training_plan (
    plan_id bigint unsigned NOT NULL COMMENT 'training plan id',
    user_id bigint unsigned NOT NULL COMMENT 'user id',
    plan_title varchar(100) NOT NULL COMMENT 'plan title',
    plan_goal varchar(255) DEFAULT NULL COMMENT 'plan goal',
    source_type varchar(32) NOT NULL COMMENT 'source type',
    based_on_exam_id bigint unsigned DEFAULT NULL COMMENT 'based on exam id',
    plan_status tinyint NOT NULL DEFAULT 0 COMMENT '0 pending 1 active 2 done 3 expired',
    ai_summary text COMMENT 'ai summary',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (plan_id),
    KEY idx_training_plan_user_id (user_id),
    KEY idx_training_plan_status (plan_status),
    KEY idx_training_plan_exam_id (based_on_exam_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='training plan';

CREATE TABLE IF NOT EXISTS tb_training_task (
    task_id bigint unsigned NOT NULL COMMENT 'training task id',
    plan_id bigint unsigned NOT NULL COMMENT 'training plan id',
    user_id bigint unsigned NOT NULL COMMENT 'user id',
    task_type varchar(20) NOT NULL COMMENT 'question test or review',
    question_id bigint unsigned DEFAULT NULL COMMENT 'related question id',
    exam_id bigint unsigned DEFAULT NULL COMMENT 'related exam id',
    title_snapshot varchar(100) NOT NULL COMMENT 'title snapshot',
    task_order int NOT NULL COMMENT 'task order',
    task_status tinyint NOT NULL DEFAULT 0 COMMENT '0 pending 1 done 2 skipped',
    recommended_reason varchar(500) DEFAULT NULL COMMENT 'reason',
    knowledge_tags_snapshot varchar(500) DEFAULT NULL COMMENT 'knowledge tags snapshot',
    due_time datetime DEFAULT NULL COMMENT 'due time',
    create_by bigint unsigned NOT NULL COMMENT 'creator',
    create_time datetime NOT NULL COMMENT 'created time',
    update_by bigint unsigned DEFAULT NULL COMMENT 'updater',
    update_time datetime DEFAULT NULL COMMENT 'updated time',
    PRIMARY KEY (task_id),
    KEY idx_training_task_plan_id (plan_id),
    KEY idx_training_task_user_id (user_id),
    KEY idx_training_task_status (task_status),
    KEY idx_training_task_question_id (question_id),
    KEY idx_training_task_exam_id (exam_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='training task';

SET FOREIGN_KEY_CHECKS = 1;

-- Demo seed data
INSERT INTO tb_sys_user (
    user_id, user_account, nick_name, password, create_by, create_time, update_by, update_time
) VALUES (
    1, 'admin', 'Admin', '$2a$10$S0hCQni3rpH/NObOlIFnWO9LOkyRgunMs34rX9UpGe2FENd1yke/m', 1, NOW(), 1, NOW()
)
ON DUPLICATE KEY UPDATE
    nick_name = VALUES(nick_name),
    password = VALUES(password),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);

INSERT INTO tb_user (
    user_id, nick_name, head_image, sex, phone, code, email, wechat, school_name, major_name, introduce, status, create_by, create_time, update_by, update_time
) VALUES
    (10001, 'Demo Learner', 'https://api.dicebear.com/9.x/thumbs/svg?seed=syncode-user-1', 1, NULL, NULL, 'demo_user_1@syncode.dev', NULL, 'UESTC', 'Software Engineering', 'Starter learner focused on arrays and strings.', 1, 1, NOW(), 1, NOW()),
    (10002, 'Practice Bot', 'https://api.dicebear.com/9.x/thumbs/svg?seed=syncode-user-2', 2, NULL, NULL, 'demo_user_2@syncode.dev', NULL, 'SCU', 'Computer Science', 'Wants a structured plan for algorithm progress.', 1, 1, NOW(), 1, NOW()),
    (10003, 'Contest User', 'https://api.dicebear.com/9.x/thumbs/svg?seed=syncode-user-3', 1, NULL, NULL, 'demo_user_3@syncode.dev', NULL, 'CQU', 'Artificial Intelligence', 'Joins weekly contests and training tasks.', 1, 1, NOW(), 1, NOW())
ON DUPLICATE KEY UPDATE
    nick_name = VALUES(nick_name),
    head_image = VALUES(head_image),
    sex = VALUES(sex),
    email = VALUES(email),
    school_name = VALUES(school_name),
    major_name = VALUES(major_name),
    introduce = VALUES(introduce),
    status = VALUES(status),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);

INSERT INTO tb_question (
    question_id, title, difficulty, algorithm_tag, knowledge_tags, estimated_minutes, training_enabled,
    time_limit, space_limit, content, question_case, default_code, main_fuc,
    create_by, create_time, update_by, update_time
) VALUES
    (
        20001,
        'Two Sum A Plus B',
        1,
        'array',
        'array,hash,simulation',
        15,
        1,
        1000,
        131072,
        'Given two integers, print their sum.',
        '[{"input":"1 2","output":"3"},{"input":"4 5","output":"9"}]',
        'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner in = new Scanner(System.in);\n        int a = in.nextInt();\n        int b = in.nextInt();\n        System.out.println(a + b);\n    }\n}',
        'public static void main(String[] args)',
        1, NOW(), 1, NOW()
    ),
    (
        20002,
        'Valid Parentheses',
        2,
        'stack',
        'stack,string',
        20,
        1,
        1000,
        131072,
        'Given a bracket string, determine whether it is valid.',
        '[{"input":"()[]{}","output":"true"},{"input":"([)]","output":"false"}]',
        'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner in = new Scanner(System.in);\n        String s = in.nextLine();\n        System.out.println(isValid(s));\n    }\n    static boolean isValid(String s) {\n        Deque<Character> stack = new ArrayDeque<>();\n        for (char c : s.toCharArray()) {\n            if (c == ''('' || c == ''['' || c == ''{'') stack.push(c);\n            else {\n                if (stack.isEmpty()) return false;\n                char top = stack.pop();\n                if ((c == '')'' && top != ''('') || (c == '']'' && top != ''['') || (c == ''}'' && top != ''{'')) return false;\n            }\n        }\n        return stack.isEmpty();\n    }\n}',
        'public static void main(String[] args)',
        1, NOW(), 1, NOW()
    ),
    (
        20003,
        'Binary Search',
        1,
        'binary_search',
        'binary_search,array',
        15,
        1,
        1000,
        131072,
        'Find the target index in a sorted array, or print -1.',
        '[{"input":"5\n1 3 5 7 9\n7","output":"3"},{"input":"5\n1 3 5 7 9\n4","output":"-1"}]',
        'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner in = new Scanner(System.in);\n        int n = Integer.parseInt(in.nextLine().trim());\n        int[] nums = new int[n];\n        for (int i = 0; i < n; i++) nums[i] = in.nextInt();\n        int target = in.nextInt();\n        int left = 0, right = n - 1, ans = -1;\n        while (left <= right) {\n            int mid = left + (right - left) / 2;\n            if (nums[mid] == target) { ans = mid; break; }\n            if (nums[mid] < target) left = mid + 1; else right = mid - 1;\n        }\n        System.out.println(ans);\n    }\n}',
        'public static void main(String[] args)',
        1, NOW(), 1, NOW()
    ),
    (
        20004,
        'Number of Islands',
        3,
        'graph_search',
        'dfs,bfs,grid',
        35,
        1,
        2000,
        262144,
        'Count the number of islands in a 0/1 grid.',
        '[{"input":"4 5\n11000\n11000\n00100\n00011","output":"3"}]',
        'import java.util.*;\npublic class Main {\n    static int[] dx = {1,-1,0,0};\n    static int[] dy = {0,0,1,-1};\n    public static void main(String[] args) {\n        Scanner in = new Scanner(System.in);\n        int n = in.nextInt();\n        int m = in.nextInt();\n        char[][] grid = new char[n][m];\n        for (int i = 0; i < n; i++) grid[i] = in.next().toCharArray();\n        int count = 0;\n        for (int i = 0; i < n; i++) {\n            for (int j = 0; j < m; j++) {\n                if (grid[i][j] == ''1'') {\n                    count++;\n                    dfs(grid, i, j);\n                }\n            }\n        }\n        System.out.println(count);\n    }\n    static void dfs(char[][] g, int x, int y) {\n        if (x < 0 || y < 0 || x >= g.length || y >= g[0].length || g[x][y] != ''1'') return;\n        g[x][y] = ''0'';\n        for (int k = 0; k < 4; k++) dfs(g, x + dx[k], y + dy[k]);\n    }\n}',
        'public static void main(String[] args)',
        1, NOW(), 1, NOW()
    ),
    (
        20005,
        'Longest Increasing Subsequence',
        2,
        'dynamic_programming',
        'dp,greedy,binary_search',
        30,
        1,
        2000,
        262144,
        'Return the length of the longest strictly increasing subsequence.',
        '[{"input":"8\n10 9 2 5 3 7 101 18","output":"4"}]',
        'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner in = new Scanner(System.in);\n        int n = in.nextInt();\n        int[] tails = new int[n];\n        int size = 0;\n        for (int i = 0; i < n; i++) {\n            int x = in.nextInt();\n            int l = 0, r = size;\n            while (l < r) {\n                int mid = (l + r) >>> 1;\n                if (tails[mid] < x) l = mid + 1; else r = mid;\n            }\n            tails[l] = x;\n            if (l == size) size++;\n        }\n        System.out.println(size);\n    }\n}',
        'public static void main(String[] args)',
        1, NOW(), 1, NOW()
    )
ON DUPLICATE KEY UPDATE
    title = VALUES(title),
    difficulty = VALUES(difficulty),
    algorithm_tag = VALUES(algorithm_tag),
    knowledge_tags = VALUES(knowledge_tags),
    estimated_minutes = VALUES(estimated_minutes),
    training_enabled = VALUES(training_enabled),
    time_limit = VALUES(time_limit),
    space_limit = VALUES(space_limit),
    content = VALUES(content),
    question_case = VALUES(question_case),
    default_code = VALUES(default_code),
    main_fuc = VALUES(main_fuc),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);

INSERT INTO tb_exam (
    exam_id, title, start_time, end_time, status, create_by, create_time, update_by, update_time
) VALUES
    (30001, 'Algorithm Weekly Test', DATE_ADD(NOW(), INTERVAL 1 DAY), DATE_ADD(DATE_ADD(NOW(), INTERVAL 1 DAY), INTERVAL 90 MINUTE), 1, 1, NOW(), 1, NOW()),
    (30002, 'Graph Search Sprint', DATE_ADD(NOW(), INTERVAL 3 DAY), DATE_ADD(DATE_ADD(NOW(), INTERVAL 3 DAY), INTERVAL 120 MINUTE), 1, 1, NOW(), 1, NOW())
ON DUPLICATE KEY UPDATE
    title = VALUES(title),
    start_time = VALUES(start_time),
    end_time = VALUES(end_time),
    status = VALUES(status),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);

INSERT INTO tb_exam_question (
    exam_question_id, question_id, exam_id, question_order, create_by, create_time, update_by, update_time
) VALUES
    (31001, 20001, 30001, 1, 1, NOW(), 1, NOW()),
    (31002, 20003, 30001, 2, 1, NOW(), 1, NOW()),
    (31003, 20002, 30001, 3, 1, NOW(), 1, NOW()),
    (31004, 20004, 30002, 1, 1, NOW(), 1, NOW()),
    (31005, 20005, 30002, 2, 1, NOW(), 1, NOW())
ON DUPLICATE KEY UPDATE
    question_id = VALUES(question_id),
    exam_id = VALUES(exam_id),
    question_order = VALUES(question_order),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);

INSERT INTO tb_user_exam (
    user_exam_id, user_id, exam_id, score, exam_rank, create_by, create_time, update_by, update_time
) VALUES
    (32001, 10001, 30001, 180, 2, 1, NOW(), 1, NOW()),
    (32002, 10002, 30001, 200, 1, 1, NOW(), 1, NOW()),
    (32003, 10003, 30002, 160, 1, 1, NOW(), 1, NOW())
ON DUPLICATE KEY UPDATE
    score = VALUES(score),
    exam_rank = VALUES(exam_rank),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);

INSERT INTO tb_user_submit (
    submit_id, request_id, user_id, question_id, exam_id, program_type, user_code, pass, exe_message, score,
    case_judge_res, use_time, use_memory, judge_status, retry_count, last_error, finish_time,
    create_by, create_time, update_by, update_time
) VALUES
    (
        40001, 'seed-submit-40001', 10001, 20001, NULL, 0,
        'public class Main { public static void main(String[] args){ System.out.println(3); } }',
        1, 'Accepted', 100,
        '[{"input":"1 2","expected":"3","actual":"3","pass":true}]',
        12, 2048, 1, 0, NULL, NOW(),
        10001, DATE_SUB(NOW(), INTERVAL 5 DAY), 10001, DATE_SUB(NOW(), INTERVAL 5 DAY)
    ),
    (
        40002, 'seed-submit-40002', 10002, 20001, NULL, 0,
        'public class Main { public static void main(String[] args){ System.out.println(3); } }',
        1, 'Accepted', 100,
        '[{"input":"1 2","expected":"3","actual":"3","pass":true}]',
        15, 2200, 1, 0, NULL, NOW(),
        10002, DATE_SUB(NOW(), INTERVAL 4 DAY), 10002, DATE_SUB(NOW(), INTERVAL 4 DAY)
    ),
    (
        40003, 'seed-submit-40003', 10003, 20002, NULL, 0,
        'public class Main { public static void main(String[] args){ System.out.println("true"); } }',
        1, 'Accepted', 100,
        '[{"input":"()[]{}","expected":"true","actual":"true","pass":true}]',
        18, 2400, 1, 0, NULL, NOW(),
        10003, DATE_SUB(NOW(), INTERVAL 3 DAY), 10003, DATE_SUB(NOW(), INTERVAL 3 DAY)
    ),
    (
        40004, 'seed-submit-40004', 10001, 20003, 30001, 0,
        'public class Main { public static void main(String[] args){ System.out.println(3); } }',
        1, 'Accepted', 80,
        '[{"input":"5\\n1 3 5 7 9\\n7","expected":"3","actual":"3","pass":true}]',
        20, 2600, 1, 0, NULL, NOW(),
        10001, DATE_SUB(NOW(), INTERVAL 2 DAY), 10001, DATE_SUB(NOW(), INTERVAL 2 DAY)
    ),
    (
        40005, 'seed-submit-40005', 10002, 20004, 30002, 0,
        'public class Main { public static void main(String[] args){ System.out.println(3); } }',
        0, 'Wrong Answer', 40,
        '[{"input":"4 5\\n11000\\n11000\\n00100\\n00011","expected":"3","actual":"2","pass":false}]',
        55, 4096, 1, 0, 'wrong island count', NOW(),
        10002, DATE_SUB(NOW(), INTERVAL 1 DAY), 10002, DATE_SUB(NOW(), INTERVAL 1 DAY)
    )
ON DUPLICATE KEY UPDATE
    user_id = VALUES(user_id),
    question_id = VALUES(question_id),
    exam_id = VALUES(exam_id),
    program_type = VALUES(program_type),
    user_code = VALUES(user_code),
    pass = VALUES(pass),
    exe_message = VALUES(exe_message),
    score = VALUES(score),
    case_judge_res = VALUES(case_judge_res),
    use_time = VALUES(use_time),
    use_memory = VALUES(use_memory),
    judge_status = VALUES(judge_status),
    retry_count = VALUES(retry_count),
    last_error = VALUES(last_error),
    finish_time = VALUES(finish_time),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);

INSERT INTO tb_message_text (
    text_id, message_title, message_content, create_by, create_time, update_by, update_time
) VALUES
    (50001, 'Welcome', 'Welcome to SynCode. Start with the weekly algorithm test.', 1, NOW(), 1, NOW()),
    (50002, 'Training', 'Your training plan is ready. Open the training page to review it.', 1, NOW(), 1, NOW())
ON DUPLICATE KEY UPDATE
    message_title = VALUES(message_title),
    message_content = VALUES(message_content),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);

INSERT INTO tb_message (
    message_id, text_id, send_id, rec_id, create_by, create_time, update_by, update_time
) VALUES
    (51001, 50001, 1, 10001, 1, NOW(), 1, NOW()),
    (51002, 50001, 1, 10002, 1, NOW(), 1, NOW()),
    (51003, 50002, 1, 10003, 1, NOW(), 1, NOW())
ON DUPLICATE KEY UPDATE
    text_id = VALUES(text_id),
    send_id = VALUES(send_id),
    rec_id = VALUES(rec_id),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);

INSERT INTO tb_notice (
    notice_id, title, content, category, is_public, is_pinned, status, publish_time, create_by, create_time, update_by, update_time
) VALUES
    (60001, 'Environment Ready', 'The development environment is now wired to cloud middleware and ready for full-stack smoke tests.', 'Announcement', 1, 1, 1, NOW(), 1, NOW(), 1, NOW()),
    (60002, 'Weekly Test Open', 'The weekly algorithm test is published. You can join it from the exam page.', 'Contest', 1, 0, 1, NOW(), 1, NOW(), 1, NOW()),
    (60003, 'Training Live', 'Training is now powered by the agent module. Generate a plan from the training page.', 'Feature', 1, 0, 1, NOW(), 1, NOW(), 1, NOW())
ON DUPLICATE KEY UPDATE
    title = VALUES(title),
    content = VALUES(content),
    category = VALUES(category),
    is_public = VALUES(is_public),
    is_pinned = VALUES(is_pinned),
    status = VALUES(status),
    publish_time = VALUES(publish_time),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);

INSERT INTO tb_training_profile (
    profile_id, user_id, current_level, target_direction, weak_points, strong_points, last_test_exam_id, last_plan_id,
    status, create_by, create_time, update_by, update_time
) VALUES
    (70001, 10001, 'starter', 'algorithm_foundation', 'Needs more repetition on stack and linked-list style problems.', 'Good pace on basic array simulations.', 30001, 71001, 1, 1, NOW(), 1, NOW()),
    (70002, 10002, 'intermediate', 'binary_search', 'Boundary handling in binary search is still unstable.', 'Submission rhythm is consistent and complete.', 30001, 71002, 1, 1, NOW(), 1, NOW()),
    (70003, 10003, 'intermediate', 'graph_search', 'Graph traversal still needs structured repetition.', 'Bracket matching and stack problems are solid.', 30002, 71003, 1, 1, NOW(), 1, NOW())
ON DUPLICATE KEY UPDATE
    current_level = VALUES(current_level),
    target_direction = VALUES(target_direction),
    weak_points = VALUES(weak_points),
    strong_points = VALUES(strong_points),
    last_test_exam_id = VALUES(last_test_exam_id),
    last_plan_id = VALUES(last_plan_id),
    status = VALUES(status),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);

INSERT INTO tb_training_plan (
    plan_id, user_id, plan_title, plan_goal, source_type, based_on_exam_id, plan_status, ai_summary,
    create_by, create_time, update_by, update_time
) VALUES
    (71001, 10001, 'Three Day Foundation Plan', 'Close basic gaps first, then take one consolidation test.', 'manual_seed', 30001, 1, 'Start with fundamentals and finish with a weekly test review.', 1, NOW(), 1, NOW()),
    (71002, 10002, 'Binary Search Boost', 'Focus on binary search and boundary control.', 'manual_seed', 30001, 1, 'Use one binary-search drill and one short test to verify progress.', 1, NOW(), 1, NOW()),
    (71003, 10003, 'Graph Search Starter', 'Start from DFS/BFS basics and then try the graph sprint.', 'manual_seed', 30002, 1, 'Solve islands first, then enter the graph sprint.', 1, NOW(), 1, NOW())
ON DUPLICATE KEY UPDATE
    plan_title = VALUES(plan_title),
    plan_goal = VALUES(plan_goal),
    source_type = VALUES(source_type),
    based_on_exam_id = VALUES(based_on_exam_id),
    plan_status = VALUES(plan_status),
    ai_summary = VALUES(ai_summary),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);

INSERT INTO tb_training_task (
    task_id, plan_id, user_id, task_type, question_id, exam_id, title_snapshot, task_order, task_status,
    recommended_reason, knowledge_tags_snapshot, due_time, create_by, create_time, update_by, update_time
) VALUES
    (72001, 71001, 10001, 'question', 20001, NULL, 'Two Sum A Plus B', 1, 1, 'Warm up and recover coding rhythm.', 'array,hash,simulation', DATE_ADD(NOW(), INTERVAL 1 DAY), 1, NOW(), 1, NOW()),
    (72002, 71001, 10001, 'question', 20002, NULL, 'Valid Parentheses', 2, 0, 'Add one stack problem to the plan.', 'stack,string', DATE_ADD(NOW(), INTERVAL 2 DAY), 1, NOW(), 1, NOW()),
    (72003, 71001, 10001, 'exam', NULL, 30001, 'Algorithm Weekly Test', 3, 0, 'Use one contest-style test for validation.', 'array,binary_search,stack', DATE_ADD(NOW(), INTERVAL 3 DAY), 1, NOW(), 1, NOW()),
    (72004, 71002, 10002, 'question', 20003, NULL, 'Binary Search', 1, 0, 'Core drill for this direction.', 'binary_search,array', DATE_ADD(NOW(), INTERVAL 1 DAY), 1, NOW(), 1, NOW()),
    (72005, 71002, 10002, 'question', 20005, NULL, 'Longest Increasing Subsequence', 2, 0, 'Combine binary search with dynamic programming.', 'dp,greedy,binary_search', DATE_ADD(NOW(), INTERVAL 2 DAY), 1, NOW(), 1, NOW()),
    (72006, 71003, 10003, 'question', 20004, NULL, 'Number of Islands', 1, 0, 'Start from one grid-search classic.', 'dfs,bfs,grid', DATE_ADD(NOW(), INTERVAL 1 DAY), 1, NOW(), 1, NOW()),
    (72007, 71003, 10003, 'exam', NULL, 30002, 'Graph Search Sprint', 2, 0, 'Use the sprint to test graph-search fluency.', 'graph_search,graph', DATE_ADD(NOW(), INTERVAL 3 DAY), 1, NOW(), 1, NOW())
ON DUPLICATE KEY UPDATE
    plan_id = VALUES(plan_id),
    user_id = VALUES(user_id),
    task_type = VALUES(task_type),
    question_id = VALUES(question_id),
    exam_id = VALUES(exam_id),
    title_snapshot = VALUES(title_snapshot),
    task_order = VALUES(task_order),
    task_status = VALUES(task_status),
    recommended_reason = VALUES(recommended_reason),
    knowledge_tags_snapshot = VALUES(knowledge_tags_snapshot),
    due_time = VALUES(due_time),
    update_by = VALUES(update_by),
    update_time = VALUES(update_time);
