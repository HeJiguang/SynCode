package com.sintao.common.mybatis;

import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.utils.ThreadLocalUtil;
import org.apache.ibatis.reflection.MetaObject;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

@Component
public class MyMetaObjectHandler implements MetaObjectHandler {

    private Long currentUserIdOrSystem() {
        Long userId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        return userId != null ? userId : Constants.SYSTEM_USER_ID;
    }

    @Override
    public void insertFill(MetaObject metaObject) {
        this.strictInsertFill(metaObject, "createTime", LocalDateTime.class, LocalDateTime.now());
        this.strictInsertFill(metaObject, "createBy", Long.class, currentUserIdOrSystem());
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        this.setFieldValByName("updateTime", LocalDateTime.now(), metaObject);
        this.setFieldValByName("updateBy", currentUserIdOrSystem(), metaObject);
    }
}
