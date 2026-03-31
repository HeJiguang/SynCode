package com.sintao.friend.service.user.impl;

import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.sintao.common.core.constants.CacheConstants;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.constants.HttpConstants;
import com.sintao.common.core.domain.LoginUser;
import com.sintao.common.core.domain.R;
import com.sintao.common.core.domain.vo.LoginUserVO;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.enums.UserIdentity;
import com.sintao.common.core.enums.UserStatus;
import com.sintao.common.core.utils.ThreadLocalUtil;
import com.sintao.common.message.service.MailService;
import com.sintao.common.redis.service.RedisService;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.common.security.service.TokenService;
import com.sintao.friend.domain.user.User;
import com.sintao.friend.domain.user.dto.UserDTO;
import com.sintao.friend.domain.user.dto.UserUpdateDTO;
import com.sintao.friend.domain.user.vo.UserDashboardSummaryVO;
import com.sintao.friend.domain.user.vo.UserHeatmapPointVO;
import com.sintao.friend.domain.user.vo.UserVO;
import com.sintao.friend.manager.UserCacheManager;
import com.sintao.friend.mapper.user.UserMapper;
import com.sintao.friend.mapper.user.UserSubmitMapper;
import com.sintao.friend.service.user.IUserService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;
import java.time.temporal.ChronoUnit;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
@Slf4j
public class UserServiceImpl implements IUserService {

    private static final Pattern EMAIL_PATTERN =
            Pattern.compile("^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$");

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private TokenService tokenService;

    @Autowired
    private MailService mailService;

    @Autowired
    private RedisService redisService;

    @Autowired
    private UserCacheManager userCacheManager;

    @Autowired
    private UserSubmitMapper userSubmitMapper;

    @Value("${mail.code-expiration:5}")
    private Long emailCodeExpiration;

    @Value("${mail.send-limit:3}")
    private Integer sendLimit;

    @Value("${mail.is-send:false}")
    private boolean isSend;

    @Value("${jwt.secret}")
    private String secret;

    @Value("${file.oss.downloadUrl}")
    private String downloadUrl;

    @Override
    public boolean sendCode(UserDTO userDTO) {
        String email = userDTO.getEmail();
        if (!checkEmail(email)) {
            throw new ServiceException(ResultCode.FAILED_USER_EMAIL);
        }

        String emailCodeKey = getEmailCodeKey(email);
        Long expire = redisService.getExpire(emailCodeKey, TimeUnit.SECONDS);
        if (expire != null && expire > 0 && (emailCodeExpiration * 60 - expire) < 60) {
            throw new ServiceException(ResultCode.FAILED_FREQUENT);
        }

        String codeTimeKey = getEmailCodeTimeKey(email);
        Long sendTimes = redisService.getCacheObject(codeTimeKey, Long.class);
        if (sendTimes != null && sendTimes >= sendLimit) {
            throw new ServiceException(ResultCode.FAILED_TIME_LIMIT);
        }

        String code = isSend ? mailService.generateCode() : Constants.DEFAULT_CODE;
        redisService.setCacheObject(emailCodeKey, code, emailCodeExpiration, TimeUnit.MINUTES);
        log.info("[email-code] email={}, code={}", email, code);

        if (isSend && !mailService.sendLoginCode(email, code)) {
            throw new ServiceException(ResultCode.FAILED_SEND_CODE);
        }

        redisService.increment(codeTimeKey);
        if (sendTimes == null) {
            LocalDateTime now = LocalDateTime.now();
            LocalDateTime nextMidnight = now.plusDays(1).withHour(0).withMinute(0).withSecond(0).withNano(0);
            long seconds = ChronoUnit.SECONDS.between(now, nextMidnight);
            redisService.expire(codeTimeKey, seconds, TimeUnit.SECONDS);
        }
        return true;
    }

    @Override
    public String codeLogin(String email, String code) {
        checkCode(email, code);
        User user = userMapper.selectOne(new LambdaQueryWrapper<User>().eq(User::getEmail, email));
        if (user == null) {
            user = new User();
            user.setEmail(email);
            user.setStatus(UserStatus.Normal.getValue());
            user.setCreateBy(Constants.SYSTEM_USER_ID);
            userMapper.insert(user);
        }
        return tokenService.createToken(
                user.getUserId(),
                secret,
                UserIdentity.ORDINARY.getValue(),
                user.getNickName(),
                user.getHeadImage()
        );
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
        if (StrUtil.isNotEmpty(loginUser.getHeadImage())) {
            loginUserVO.setHeadImage(downloadUrl + loginUser.getHeadImage());
        }
        return R.ok(loginUserVO);
    }

    @Override
    public UserVO detail() {
        Long userId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        if (userId == null) {
            throw new ServiceException(ResultCode.FAILED_USER_NOT_EXISTS);
        }
        UserVO userVO = userCacheManager.getUserById(userId);
        if (userVO == null) {
            throw new ServiceException(ResultCode.FAILED_USER_NOT_EXISTS);
        }
        if (StrUtil.isNotEmpty(userVO.getHeadImage())) {
            userVO.setHeadImage(downloadUrl + userVO.getHeadImage());
        }
        return userVO;
    }

    @Override
    public UserDashboardSummaryVO dashboardSummary() {
        Long userId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        if (userId == null) {
            throw new ServiceException(ResultCode.FAILED_USER_NOT_EXISTS);
        }

        LocalDateTime sinceTime = LocalDateTime.now().minusDays(180);
        List<UserHeatmapPointVO> heatmap = userSubmitMapper.selectHeatmap(userId, sinceTime);
        heatmap.sort(Comparator.comparing(UserHeatmapPointVO::getStudyDate).reversed());

        UserDashboardSummaryVO summaryVO = new UserDashboardSummaryVO();
        summaryVO.setSolvedCount(defaultZero(userSubmitMapper.selectSolvedQuestionCount(userId)));
        summaryVO.setSubmissionCount(defaultZero(userSubmitMapper.selectSubmissionCount(userId)));
        summaryVO.setHeatmap(heatmap);
        summaryVO.setStreakDays(calculateStreakDays(heatmap));
        return summaryVO;
    }

    @Override
    public int edit(UserUpdateDTO userUpdateDTO) {
        Long userId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        if (userId == null) {
            throw new ServiceException(ResultCode.FAILED_USER_NOT_EXISTS);
        }
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new ServiceException(ResultCode.FAILED_USER_NOT_EXISTS);
        }
        user.setNickName(userUpdateDTO.getNickName());
        user.setSex(userUpdateDTO.getSex());
        user.setSchoolName(userUpdateDTO.getSchoolName());
        user.setMajorName(userUpdateDTO.getMajorName());
        user.setPhone(userUpdateDTO.getPhone());
        user.setEmail(userUpdateDTO.getEmail());
        user.setWechat(userUpdateDTO.getWechat());
        user.setIntroduce(userUpdateDTO.getIntroduce());
        userCacheManager.refreshUser(user);
        tokenService.refreshLoginUser(
                user.getNickName(),
                user.getHeadImage(),
                ThreadLocalUtil.get(Constants.USER_KEY, String.class)
        );
        return userMapper.updateById(user);
    }

    @Override
    public int updateHeadImage(String headImage) {
        Long userId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        if (userId == null) {
            throw new ServiceException(ResultCode.FAILED_USER_NOT_EXISTS);
        }
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new ServiceException(ResultCode.FAILED_USER_NOT_EXISTS);
        }
        user.setHeadImage(headImage);
        userCacheManager.refreshUser(user);
        tokenService.refreshLoginUser(
                user.getNickName(),
                user.getHeadImage(),
                ThreadLocalUtil.get(Constants.USER_KEY, String.class)
        );
        return userMapper.updateById(user);
    }

    private void checkCode(String email, String code) {
        String emailCodeKey = getEmailCodeKey(email);
        String cacheCode = redisService.getCacheObject(emailCodeKey, String.class);
        if (StrUtil.isEmpty(cacheCode)) {
            throw new ServiceException(ResultCode.FAILED_INVALID_CODE);
        }
        if (!cacheCode.equals(code)) {
            throw new ServiceException(ResultCode.FAILED_ERROR_CODE);
        }
        redisService.deleteObject(emailCodeKey);
    }

    public static boolean checkEmail(String email) {
        if (StrUtil.isBlank(email)) {
            return false;
        }
        Matcher matcher = EMAIL_PATTERN.matcher(email);
        return matcher.matches();
    }

    private String getEmailCodeKey(String email) {
        return CacheConstants.EMAIL_CODE_KEY + email;
    }

    private String getEmailCodeTimeKey(String email) {
        return CacheConstants.EMAIL_CODE_TIME_KEY + email;
    }

    private Integer defaultZero(Integer value) {
        return value == null ? 0 : value;
    }

    private Integer calculateStreakDays(List<UserHeatmapPointVO> heatmap) {
        if (heatmap == null || heatmap.isEmpty()) {
            return 0;
        }

        int streak = 0;
        LocalDateTime cursor = LocalDateTime.now().withHour(0).withMinute(0).withSecond(0).withNano(0);
        List<String> activeDays = heatmap.stream()
                .map(UserHeatmapPointVO::getStudyDate)
                .sorted(Comparator.reverseOrder())
                .collect(Collectors.toList());

        for (String activeDay : activeDays) {
            String expected = cursor.toLocalDate().toString();
            if (expected.equals(activeDay)) {
                streak += 1;
                cursor = cursor.minusDays(1);
                continue;
            }
            if (streak == 0 && cursor.minusDays(1).toLocalDate().toString().equals(activeDay)) {
                streak += 1;
                cursor = cursor.minusDays(2);
                continue;
            }
            break;
        }
        return streak;
    }
}
