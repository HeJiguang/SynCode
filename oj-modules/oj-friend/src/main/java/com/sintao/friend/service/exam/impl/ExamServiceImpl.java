package com.sintao.friend.service.exam.impl;

import cn.hutool.core.collection.CollectionUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.domain.TableDataInfo;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.utils.ThreadLocalUtil;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.friend.domain.exam.Exam;
import com.sintao.friend.domain.exam.dto.ExamQueryDTO;
import com.sintao.friend.domain.exam.dto.ExamRankDTO;
import com.sintao.friend.domain.exam.vo.ExamRankVO;
import com.sintao.friend.domain.exam.vo.ExamVO;
import com.sintao.friend.domain.user.UserExam;
import com.sintao.friend.domain.user.vo.UserVO;
import com.sintao.friend.manager.ExamCacheManager;
import com.sintao.friend.manager.UserCacheManager;
import com.sintao.friend.mapper.exam.ExamMapper;
import com.sintao.friend.mapper.user.UserExamMapper;
import com.sintao.friend.service.exam.IExamService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
@Slf4j
public class ExamServiceImpl implements IExamService {

    @Autowired
    private ExamMapper examMapper;

    @Autowired
    private ExamCacheManager examCacheManager;

    @Autowired
    private UserCacheManager userCacheManager;

    @Autowired
    private UserExamMapper userExamMapper;

    @Override
    public List<ExamVO> list(ExamQueryDTO examQueryDTO) {
        PageHelper.startPage(examQueryDTO.getPageNum(), examQueryDTO.getPageSize());
        return examMapper.selectExamList(examQueryDTO);
    }

    @Override
    public TableDataInfo redisList(ExamQueryDTO examQueryDTO) {
        Long total = examCacheManager.getListSize(examQueryDTO.getType(), null);
        List<ExamVO> examVOList;
        if (total == null || total <= 0) {
            examVOList = list(examQueryDTO);
            examCacheManager.refreshCache(examQueryDTO.getType(), null);
            total = new PageInfo<>(examVOList).getTotal();
        } else {
            examVOList = examCacheManager.getExamVOList(examQueryDTO, null);
            total = examCacheManager.getListSize(examQueryDTO.getType(), null);
        }
        if (CollectionUtil.isEmpty(examVOList)) {
            return TableDataInfo.empty();
        }
        assembleExamVOList(examVOList);
        return TableDataInfo.success(examVOList, total);
    }

    @Override
    public TableDataInfo rankList(ExamRankDTO examRankDTO) {
        Long total = examCacheManager.getRankListSize(examRankDTO.getExamId());
        List<ExamRankVO> examRankVOList;
        if (total == null || total <= 0) {
            PageHelper.startPage(examRankDTO.getPageNum(), examRankDTO.getPageSize());
            examRankVOList = userExamMapper.selectExamRankList(examRankDTO.getExamId());
            examCacheManager.refreshExamRankCache(examRankDTO.getExamId());
            total = new PageInfo<>(examRankVOList).getTotal();
        } else {
            examRankVOList = examCacheManager.getExamRankList(examRankDTO);
        }
        if (CollectionUtil.isEmpty(examRankVOList)) {
            return TableDataInfo.empty();
        }
        assembleExamRankVOList(examRankVOList);
        return TableDataInfo.success(examRankVOList, total);
    }

    @Override
    public String getFirstQuestion(Long examId) {
        validateExamAccess(examId);
        checkAndRefresh(examId);
        return examCacheManager.getFirstQuestion(examId).toString();
    }

    @Override
    public String preQuestion(Long examId, Long questionId) {
        validateExamAccess(examId);
        checkAndRefresh(examId);
        return examCacheManager.preQuestion(examId, questionId).toString();
    }

    @Override
    public String nextQuestion(Long examId, Long questionId) {
        validateExamAccess(examId);
        checkAndRefresh(examId);
        return examCacheManager.nextQuestion(examId, questionId).toString();
    }

    private void assembleExamVOList(List<ExamVO> examVOList) {
        Long userId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        List<Long> userExamIdList = examCacheManager.getAllUserExamList(userId);
        if (CollectionUtil.isEmpty(userExamIdList)) {
            return;
        }
        for (ExamVO examVO : examVOList) {
            if (userExamIdList.contains(examVO.getExamId())) {
                examVO.setEnter(true);
            }
        }
    }

    private void assembleExamRankVOList(List<ExamRankVO> examRankVOList) {
        if (CollectionUtil.isEmpty(examRankVOList)) {
            return;
        }
        for (ExamRankVO examRankVO : examRankVOList) {
            Long userId = examRankVO.getUserId();
            UserVO user = userCacheManager.getUserById(userId);
            examRankVO.setNickName(user.getNickName());
        }
    }

    private void checkAndRefresh(Long examId) {
        Long listSize = examCacheManager.getExamQuestionListSize(examId);
        if (listSize == null || listSize <= 0) {
            examCacheManager.refreshExamQuestionCache(examId);
        }
    }

    private void validateExamAccess(Long examId) {
        Exam exam = examMapper.selectById(examId);
        if (exam == null) {
            throw new ServiceException(ResultCode.EXAM_NOT_EXISTS);
        }

        LocalDateTime now = LocalDateTime.now();
        if (exam.getStartTime() != null && now.isBefore(exam.getStartTime())) {
            throw new ServiceException(ResultCode.EXAM_NOT_STARTED);
        }
        if (exam.getEndTime() != null && now.isAfter(exam.getEndTime())) {
            throw new ServiceException(ResultCode.EXAM_IS_FINISH);
        }

        Long userId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        if (userId == null) {
            throw new ServiceException(ResultCode.FAILED_UNAUTHORIZED);
        }

        UserExam userExam = userExamMapper.selectOne(new LambdaQueryWrapper<UserExam>()
                .eq(UserExam::getExamId, examId)
                .eq(UserExam::getUserId, userId));
        if (userExam == null) {
            throw new ServiceException(ResultCode.USER_EXAM_NOT_ENTERED);
        }
    }
}
