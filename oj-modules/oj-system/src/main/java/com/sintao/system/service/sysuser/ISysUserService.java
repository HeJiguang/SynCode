package com.sintao.system.service.sysuser;

import com.sintao.common.core.domain.R;
import com.sintao.common.core.domain.vo.LoginUserVO;
import com.sintao.system.domain.sysuser.dto.SysUserSaveDTO;
import com.sintao.system.domain.sysuser.vo.SysUserVO;

public interface ISysUserService {

    R<String> login(String userAccount, String password);

    boolean logout(String token);

    R<LoginUserVO> info(String token);

    int add(SysUserSaveDTO sysUserSaveDTO);

    int delete(Long userId);

    SysUserVO detail(Long userId);
}
