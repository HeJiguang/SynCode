package com.sintao.friend.controller.user;

import com.sintao.common.core.constants.HttpConstants;
import com.sintao.common.core.controller.BaseController;
import com.sintao.common.core.domain.R;
import com.sintao.common.core.domain.vo.LoginUserVO;
import com.sintao.friend.domain.user.dto.UserDTO;
import com.sintao.friend.domain.user.dto.UserUpdateDTO;
import com.sintao.friend.domain.user.vo.UserDashboardSummaryVO;
import com.sintao.friend.domain.user.vo.UserVO;
import com.sintao.friend.service.user.IUserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/user")
@Tag(name = "C 端用户接口", description = "用户登录、注册、个人信息等接口")
public class UserController extends BaseController {

    @Autowired
    private IUserService userService;

    @PostMapping("sendCode")
    @Operation(summary = "发送验证码", description = "向指定邮箱发送邮件验证码，用于登录或注册")
    @ApiResponse(responseCode = "200", description = "发送成功")
    @ApiResponse(responseCode = "2000", description = "邮箱格式错误、发送过于频繁或超过当日限制")
    public R<Void> sendCode(@RequestBody UserDTO userDTO) {
        return toR(userService.sendCode(userDTO));
    }

    @PostMapping("/code/login")
    @Operation(summary = "验证码登录", description = "使用邮箱验证码登录，新用户自动注册")
    @ApiResponse(responseCode = "200", description = "登录成功，返回 token")
    @ApiResponse(responseCode = "2000", description = "验证码错误或已过期")
    public R<String> codeLogin(@RequestBody UserDTO userDTO) {
        return R.ok(userService.codeLogin(userDTO.getEmail(), userDTO.getCode()));
    }

    @DeleteMapping("/logout")
    @Operation(summary = "退出登录", description = "退出登录并清除服务端 token")
    @Parameter(name = HttpConstants.AUTHENTICATION, in = ParameterIn.HEADER, description = "登录凭证", required = true)
    @ApiResponse(responseCode = "200", description = "退出成功")
    public R<Void> logout(@RequestHeader(HttpConstants.AUTHENTICATION) String token) {
        return toR(userService.logout(token));
    }

    @GetMapping("/info")
    @Operation(summary = "获取当前用户信息", description = "根据 token 获取用户昵称、头像等基础信息")
    @Parameter(name = HttpConstants.AUTHENTICATION, in = ParameterIn.HEADER, description = "登录凭证", required = true)
    @ApiResponse(responseCode = "200", description = "成功返回用户信息")
    @ApiResponse(responseCode = "2000", description = "token 无效或已过期")
    public R<LoginUserVO> info(@RequestHeader(HttpConstants.AUTHENTICATION) String token) {
        return userService.info(token);
    }

    @GetMapping("/detail")
    @Operation(summary = "用户详情", description = "获取当前用户完整信息")
    @ApiResponse(responseCode = "200", description = "成功返回用户详情")
    @ApiResponse(responseCode = "2000", description = "用户不存在或未登录")
    public R<UserVO> detail() {
        return R.ok(userService.detail());
    }

    @GetMapping("/dashboard/summary")
    @Operation(summary = "用户概览", description = "返回个人中心所需的聚合统计、热力图和连续学习天数")
    @ApiResponse(responseCode = "200", description = "成功返回用户概览")
    @ApiResponse(responseCode = "2000", description = "用户不存在或未登录")
    public R<UserDashboardSummaryVO> dashboardSummary() {
        return R.ok(userService.dashboardSummary());
    }

    @PutMapping("/edit")
    @Operation(summary = "编辑用户信息", description = "更新用户昵称、性别、学校、专业等个人信息")
    @ApiResponse(responseCode = "200", description = "更新成功")
    @ApiResponse(responseCode = "2000", description = "用户不存在或更新失败")
    public R<Void> edit(@RequestBody UserUpdateDTO userUpdateDTO) {
        return toR(userService.edit(userUpdateDTO));
    }

    @PutMapping("/head-image/update")
    @Operation(summary = "更新头像", description = "更新用户头像")
    @ApiResponse(responseCode = "200", description = "更新成功")
    @ApiResponse(responseCode = "2000", description = "用户不存在或更新失败")
    public R<Void> updateHeadImage(@RequestBody UserUpdateDTO userUpdateDTO) {
        return toR(userService.updateHeadImage(userUpdateDTO.getHeadImage()));
    }
}
