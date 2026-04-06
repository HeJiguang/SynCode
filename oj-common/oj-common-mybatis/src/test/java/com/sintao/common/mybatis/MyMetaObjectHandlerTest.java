package com.sintao.common.mybatis;

import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.utils.ThreadLocalUtil;
import org.apache.ibatis.reflection.SystemMetaObject;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class MyMetaObjectHandlerTest {

    private final MyMetaObjectHandler handler = new MyMetaObjectHandler();

    @AfterEach
    void tearDown() {
        ThreadLocalUtil.remove();
    }

    @Test
    void currentUserIdFallsBackToSystemUserWhenThreadLocalUserMissing() throws Exception {
        Method method = MyMetaObjectHandler.class.getDeclaredMethod("currentUserIdOrSystem");
        method.setAccessible(true);

        Object userId = method.invoke(handler);

        assertEquals(Constants.SYSTEM_USER_ID, userId);
    }

    @Test
    void updateFillUsesThreadLocalUserWhenAvailable() {
        AuditRecord record = new AuditRecord();
        ThreadLocalUtil.set(Constants.USER_ID, 99L);

        handler.updateFill(SystemMetaObject.forObject(record));

        assertNotNull(record.updateTime);
        assertEquals(99L, record.updateBy);
    }

    private static final class AuditRecord {
        private LocalDateTime createTime;
        private Long createBy;
        private LocalDateTime updateTime;
        private Long updateBy;
    }
}
