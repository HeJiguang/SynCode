package com.sintao.system.service.sysuser.impl;

import cn.hutool.core.collection.CollectionUtil;
import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.sintao.common.core.constants.HttpConstants;
import com.sintao.common.core.domain.LoginUser;
import com.sintao.common.core.domain.R;
import com.sintao.common.core.domain.vo.LoginUserVO;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.enums.UserIdentity;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.common.security.service.TokenService;
import com.sintao.system.domain.sysuser.SysUser;
import com.sintao.system.domain.sysuser.dto.SysUserSaveDTO;
import com.sintao.system.domain.sysuser.vo.SysUserVO;
import com.sintao.system.mapper.sysuser.SysUserMapper;
import com.sintao.system.service.sysuser.ISysUserService;
import com.sintao.system.utils.BCryptUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RefreshScope
@Slf4j
public class SysUserServiceImpl implements ISysUserService {

    @Autowired
    private SysUserMapper sysUserMapper;

    @Autowired
    private TokenService tokenService;

    @Value("${jwt.secret}")
    private String secret;

    @Override
    public R<String> login(String userAccount, String password) {
        LambdaQueryWrapper<SysUser> queryWrapper = new LambdaQueryWrapper<>();
        SysUser sysUser = sysUserMapper.selectOne(queryWrapper
                .select(SysUser::getUserId, SysUser::getPassword, SysUser::getNickName)
                .eq(SysUser::getUserAccount, userAccount));
        if (sysUser == null) {
            return R.fail(ResultCode.FAILED_USER_NOT_EXISTS);
        }
        if (BCryptUtils.matchesPassword(password, sysUser.getPassword())) {
            return R.ok(tokenService.createToken(
                    sysUser.getUserId(),
                    secret,
                    UserIdentity.ADMIN.getValue(),
                    sysUser.getNickName(),
                    null
            ));
        }
        return R.fail(ResultCode.FAILED_LOGIN);
    }

    @Override
    public boolean logout(String token) {
        if (StrUtil.isNotEmpty(token) && token.startsWith(HttpConstants.PREFIX)) {
            token = token.replaceFirst(HttpConstants.PREFIX, StrUtil.EMPTY);
        }
        return tokenService.deleteLoginUser(token, secret);
    }

    @Override
    public R<LoginUserVO> info(String token) {
        if (StrUtil.isNotEmpty(token) && token.startsWith(HttpConstants.PREFIX)) {
            token = token.replaceFirst(HttpConstants.PREFIX, StrUtil.EMPTY);
        }
        LoginUser loginUser = tokenService.getLoginUser(token, secret);
        if (loginUser == null) {
            return R.fail();
        }
        LoginUserVO loginUserVO = new LoginUserVO();
        loginUserVO.setNickName(loginUser.getNickName());
        return R.ok(loginUserVO);
    }

    @Override
    public int add(SysUserSaveDTO sysUserSaveDTO) {
        List<SysUser> sysUserList = sysUserMapper.selectList(new LambdaQueryWrapper<SysUser>()
                .eq(SysUser::getUserAccount, sysUserSaveDTO.getUserAccount()));
        if (CollectionUtil.isNotEmpty(sysUserList)) {
            throw new ServiceException(ResultCode.FAILED_USER_EXISTS);
        }
        SysUser sysUser = new SysUser();
        sysUser.setUserAccount(sysUserSaveDTO.getUserAccount());
        sysUser.setPassword(BCryptUtils.encryptPassword(sysUserSaveDTO.getPassword()));
        return sysUserMapper.insert(sysUser);
    }

    @Override
    public int delete(Long userId) {
        SysUser sysUser = sysUserMapper.selectById(userId);
        if (sysUser == null) {
            throw new ServiceException(ResultCode.FAILED_USER_NOT_EXISTS);
        }
        return sysUserMapper.deleteById(userId);
    }

    @Override
    public SysUserVO detail(Long userId) {
        SysUser sysUser = sysUserMapper.selectById(userId);
        if (sysUser == null) {
            throw new ServiceException(ResultCode.FAILED_USER_NOT_EXISTS);
        }
        SysUserVO sysUserVO = new SysUserVO();
        sysUserVO.setUserAccount(sysUser.getUserAccount());
        sysUserVO.setNickName(sysUser.getNickName());
        return sysUserVO;
    }
}
