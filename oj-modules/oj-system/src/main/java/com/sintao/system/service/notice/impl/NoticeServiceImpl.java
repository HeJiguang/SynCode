package com.sintao.system.service.notice.impl;

import cn.hutool.core.bean.BeanUtil;
import com.github.pagehelper.PageHelper;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.system.domain.notice.Notice;
import com.sintao.system.domain.notice.dto.NoticeAddDTO;
import com.sintao.system.domain.notice.dto.NoticeEditDTO;
import com.sintao.system.domain.notice.dto.NoticeQueryDTO;
import com.sintao.system.domain.notice.vo.NoticeDetailVO;
import com.sintao.system.domain.notice.vo.NoticeVO;
import com.sintao.system.mapper.notice.NoticeMapper;
import com.sintao.system.service.notice.INoticeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class NoticeServiceImpl implements INoticeService {

    @Autowired
    private NoticeMapper noticeMapper;

    @Override
    public List<NoticeVO> list(NoticeQueryDTO noticeQueryDTO) {
        PageHelper.startPage(noticeQueryDTO.getPageNum(), noticeQueryDTO.getPageSize());
        return noticeMapper.selectNoticeList(noticeQueryDTO);
    }

    @Override
    public boolean add(NoticeAddDTO noticeAddDTO) {
        Notice notice = new Notice();
        BeanUtil.copyProperties(noticeAddDTO, notice);
        if (notice.getCategory() == null || notice.getCategory().isBlank()) {
            notice.setCategory("公告");
        }
        if (notice.getIsPublic() == null) {
            notice.setIsPublic(Constants.TRUE);
        }
        if (notice.getIsPinned() == null) {
            notice.setIsPinned(Constants.FALSE);
        }
        notice.setStatus(Constants.FALSE);
        notice.setPublishTime(null);
        return noticeMapper.insert(notice) > 0;
    }

    @Override
    public NoticeDetailVO detail(Long noticeId) {
        Notice notice = getNotice(noticeId);
        NoticeDetailVO detailVO = new NoticeDetailVO();
        BeanUtil.copyProperties(notice, detailVO);
        return detailVO;
    }

    @Override
    public int edit(NoticeEditDTO noticeEditDTO) {
        Notice notice = getNotice(noticeEditDTO.getNoticeId());
        notice.setTitle(noticeEditDTO.getTitle());
        notice.setContent(noticeEditDTO.getContent());
        notice.setCategory(defaultCategory(noticeEditDTO.getCategory()));
        notice.setIsPublic(defaultFlag(noticeEditDTO.getIsPublic(), Constants.TRUE));
        notice.setIsPinned(defaultFlag(noticeEditDTO.getIsPinned(), Constants.FALSE));
        return noticeMapper.updateById(notice);
    }

    @Override
    public int delete(Long noticeId) {
        getNotice(noticeId);
        return noticeMapper.deleteById(noticeId);
    }

    @Override
    public int publish(Long noticeId) {
        Notice notice = getNotice(noticeId);
        notice.setStatus(Constants.TRUE);
        notice.setPublishTime(LocalDateTime.now());
        return noticeMapper.updateById(notice);
    }

    @Override
    public int cancelPublish(Long noticeId) {
        Notice notice = getNotice(noticeId);
        notice.setStatus(Constants.FALSE);
        return noticeMapper.updateById(notice);
    }

    @Override
    public int pin(Long noticeId, Integer pinned) {
        Notice notice = getNotice(noticeId);
        notice.setIsPinned(defaultFlag(pinned, Constants.FALSE));
        return noticeMapper.updateById(notice);
    }

    private Notice getNotice(Long noticeId) {
        Notice notice = noticeMapper.selectById(noticeId);
        if (notice == null) {
            throw new ServiceException(ResultCode.FAILED_NOT_EXISTS);
        }
        return notice;
    }

    private String defaultCategory(String category) {
        return category == null || category.isBlank() ? "公告" : category;
    }

    private Integer defaultFlag(Integer value, Integer defaultValue) {
        return value == null ? defaultValue : value;
    }
}
