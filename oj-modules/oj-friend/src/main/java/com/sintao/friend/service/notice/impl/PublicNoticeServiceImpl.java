package com.sintao.friend.service.notice.impl;

import cn.hutool.core.collection.CollectionUtil;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.sintao.common.core.domain.PageQueryDTO;
import com.sintao.common.core.domain.TableDataInfo;
import com.sintao.friend.domain.notice.vo.PublicNoticeVO;
import com.sintao.friend.mapper.notice.NoticeMapper;
import com.sintao.friend.service.notice.IPublicNoticeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class PublicNoticeServiceImpl implements IPublicNoticeService {

    @Autowired
    private NoticeMapper noticeMapper;

    @Override
    public TableDataInfo list(PageQueryDTO dto) {
        PageHelper.startPage(dto.getPageNum(), dto.getPageSize());
        List<PublicNoticeVO> noticeList = noticeMapper.selectPublicNoticeList();
        if (CollectionUtil.isEmpty(noticeList)) {
            return TableDataInfo.empty();
        }
        long total = new PageInfo<>(noticeList).getTotal();
        return TableDataInfo.success(noticeList, total);
    }
}
