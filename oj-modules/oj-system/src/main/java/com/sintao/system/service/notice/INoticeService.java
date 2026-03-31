package com.sintao.system.service.notice;

import com.sintao.system.domain.notice.dto.NoticeAddDTO;
import com.sintao.system.domain.notice.dto.NoticeEditDTO;
import com.sintao.system.domain.notice.dto.NoticeQueryDTO;
import com.sintao.system.domain.notice.vo.NoticeDetailVO;
import com.sintao.system.domain.notice.vo.NoticeVO;

import java.util.List;

public interface INoticeService {

    List<NoticeVO> list(NoticeQueryDTO noticeQueryDTO);

    boolean add(NoticeAddDTO noticeAddDTO);

    NoticeDetailVO detail(Long noticeId);

    int edit(NoticeEditDTO noticeEditDTO);

    int delete(Long noticeId);

    int publish(Long noticeId);

    int cancelPublish(Long noticeId);

    int pin(Long noticeId, Integer pinned);
}
