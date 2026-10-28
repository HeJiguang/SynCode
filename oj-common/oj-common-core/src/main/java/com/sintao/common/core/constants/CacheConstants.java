package com.sintao.common.core.constants;

public class CacheConstants {

    public static final String LOGIN_TOKEN_KEY = "logintoken:";

    public static final long EXP = 720;

    public static final long REFRESH_TIME = 3;

    public static final String PHONE_CODE_KEY = "p:c:";

    public static final String EMAIL_CODE_KEY = "e:c:";

    public static final String CODE_TIME_KEY = "c:t:";

    public static final String EMAIL_CODE_TIME_KEY = "e:t:";

    public static final String EXAM_UNFINISHED_LIST = "e:t:l";

    public static final String EXAM_HISTORY_LIST = "e:h:l";

    public static final String EXAM_DETAIL = "e:d:";

    public static final String USER_EXAM_LIST = "u:e:l:";

    public static final String USER_DETAIL = "u:d:";

    public static final long USER_EXP = 10;

    public static final String USER_UPLOAD_TIMES_KEY = "u:u:t";

    public static final String QUESTION_LIST = "q:{navigation}:list";

    public static final String QUESTION_HOST_LIST = "q:{hot}:list";

    public static final String EXAM_QUESTION_LIST = "e:q:l:";

    public static final String JUDGE_REQUEST_LOCK = "j:r:l:";

    public static final String JUDGE_RUNTIME_STATE = "j:r:s:";

    public static final String JUDGE_RESULT_CACHE = "j:r:c:";

    public static final String JUDGE_RESULT_TOPIC = "j:r:t";

    public static final String USER_MESSAGE_LIST = "u:m:l:";

    public static final String MESSAGE_DETAIL = "m:d:";

    public static final String EXAM_RANK_LIST = "e:r:l:";

    public static final long DEFAULT_START = 0;

    public static final long DEFAULT_END = -1;

    private CacheConstants() {
    }
}
