package com.sintao.friend.mapper.notice;

import com.sintao.friend.domain.notice.vo.PublicNoticeVO;

import java.util.List;

public interface NoticeMapper {

    List<PublicNoticeVO> selectPublicNoticeList();
}
