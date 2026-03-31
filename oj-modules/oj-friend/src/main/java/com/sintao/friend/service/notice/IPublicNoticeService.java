package com.sintao.friend.service.notice;

import com.sintao.common.core.domain.PageQueryDTO;
import com.sintao.common.core.domain.TableDataInfo;

public interface IPublicNoticeService {

    TableDataInfo list(PageQueryDTO dto);
}
