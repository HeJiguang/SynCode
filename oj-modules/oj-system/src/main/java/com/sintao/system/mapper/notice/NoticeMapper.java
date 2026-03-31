package com.sintao.system.mapper.notice;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.sintao.system.domain.notice.Notice;
import com.sintao.system.domain.notice.dto.NoticeQueryDTO;
import com.sintao.system.domain.notice.vo.NoticeVO;

import java.util.List;

public interface NoticeMapper extends BaseMapper<Notice> {

    List<NoticeVO> selectNoticeList(NoticeQueryDTO noticeQueryDTO);
}
