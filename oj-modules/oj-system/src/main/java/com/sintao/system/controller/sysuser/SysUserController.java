package com.sintao.system.controller.sysuser;

import com.sintao.common.core.constants.HttpConstants;
import com.sintao.common.core.controller.BaseController;
import com.sintao.common.core.domain.R;
import com.sintao.common.core.domain.vo.LoginUserVO;
import com.sintao.system.domain.sysuser.dto.LoginDTO;
import com.sintao.system.domain.sysuser.dto.SysUserSaveDTO;
import com.sintao.system.domain.sysuser.vo.SysUserVO;
import com.sintao.system.service.sysuser.ISysUserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.Parameters;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/sysUser")
@Tag(name = "管理员接口")
public class SysUserController extends BaseController {

    @Autowired
    private ISysUserService sysUserService;

    @PostMapping("/login")
    @Operation(summary = "管理员登录", description = "根据账号密码进行管理员登录")
    @ApiResponse(responseCode = "1000", description = "操作成功")
    @ApiResponse(responseCode = "2000", description = "服务繁忙，请稍后重试")
    @ApiResponse(responseCode = "3102", description = "用户不存在")
    @ApiResponse(responseCode = "3103", description = "用户名或密码错误")
    public R<String> login(@RequestBody LoginDTO loginDTO) {
        return sysUserService.login(loginDTO.getUserAccount(), loginDTO.getPassword());
    }

    @DeleteMapping("/logout")
    @Operation(summary = "管理员登出", description = "清除当前登录态，需要在请求头携带 Authorization token")
    @Parameter(name = HttpConstants.AUTHENTICATION, in = ParameterIn.HEADER, description = "登录后返回的 token", required = true)
    @ApiResponse(responseCode = "1000", description = "登出成功")
    @ApiResponse(responseCode = "2000", description = "服务繁忙，请稍后重试")
    public R<Void> logout(@RequestHeader(HttpConstants.AUTHENTICATION) String token) {
        return toR(sysUserService.logout(token));
    }

    @GetMapping("/info")
    @Operation(summary = "获取当前管理员信息", description = "根据 token 获取当前登录管理员信息")
    @Parameter(name = HttpConstants.AUTHENTICATION, in = ParameterIn.HEADER, description = "登录后返回的 token", required = true)
    @ApiResponse(responseCode = "1000", description = "成功获取用户信息")
    @ApiResponse(responseCode = "2000", description = "服务繁忙，请稍后重试")
    public R<LoginUserVO> info(@RequestHeader(HttpConstants.AUTHENTICATION) String token) {
        return sysUserService.info(token);
    }

    @PostMapping("/add")
    @Operation(summary = "新增管理员", description = "根据提供的信息新增管理员")
    @ApiResponse(responseCode = "1000", description = "操作成功")
    @ApiResponse(responseCode = "2000", description = "服务繁忙，请稍后重试")
    @ApiResponse(responseCode = "3101", description = "用户已存在")
    public R<Void> add(@RequestBody SysUserSaveDTO sysUserSaveDTO) {
        return toR(sysUserService.add(sysUserSaveDTO));
    }

    @DeleteMapping("/{userId}")
    @Operation(summary = "删除管理员", description = "通过用户ID删除管理员")
    @Parameters({
            @Parameter(name = "userId", in = ParameterIn.PATH, description = "用户ID")
    })
    @ApiResponse(responseCode = "1000", description = "成功删除用户")
    @ApiResponse(responseCode = "2000", description = "服务繁忙，请稍后重试")
    @ApiResponse(responseCode = "3101", description = "用户不存在")
    public R<Void> delete(@PathVariable Long userId) {
        return toR(sysUserService.delete(userId));
    }

    @GetMapping("/detail")
    @Operation(summary = "管理员详情", description = "根据用户ID查询管理员详情")
    @Parameters({
            @Parameter(name = "userId", in = ParameterIn.QUERY, description = "用户ID"),
            @Parameter(name = "sex", in = ParameterIn.QUERY, description = "保留参数")
    })
    @ApiResponse(responseCode = "1000", description = "成功获取用户信息")
    @ApiResponse(responseCode = "2000", description = "服务繁忙，请稍后重试")
    @ApiResponse(responseCode = "3101", description = "用户不存在")
    public R<SysUserVO> detail(@RequestParam(required = true) Long userId, @RequestParam(required = false) String sex) {
        return R.ok(sysUserService.detail(userId));
    }
}
