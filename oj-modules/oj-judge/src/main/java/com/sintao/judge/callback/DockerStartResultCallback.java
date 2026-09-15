package com.sintao.judge.callback;


import cn.hutool.core.util.StrUtil;
import com.sintao.common.core.enums.CodeRunStatus;
import com.github.dockerjava.api.model.Frame;
import com.github.dockerjava.api.model.StreamType;
import com.github.dockerjava.core.command.ExecStartResultCallback;
import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;

import java.nio.charset.StandardCharsets;

@Getter
@Setter
@Slf4j
public class DockerStartResultCallback extends ExecStartResultCallback {

    private CodeRunStatus codeRunStatus;  //璁板綍鎵ц鎴愬姛杩樻槸澶辫触

    private String errorMessage;

    private String message;

    @Override
    public void onNext(Frame frame) {
        StreamType streamType = frame.getStreamType();
        if (StreamType.STDERR.equals(streamType)) {
            if (StrUtil.isEmpty(errorMessage)) {
                errorMessage = new String(frame.getPayload(), StandardCharsets.UTF_8);
            } else {
                errorMessage = errorMessage + new String(frame.getPayload(), StandardCharsets.UTF_8);
            }
            codeRunStatus = CodeRunStatus.FAILED;
        } else {
            String msgTmp = new String(frame.getPayload(), StandardCharsets.UTF_8);
            if (StrUtil.isNotEmpty(msgTmp)) {
                message = StrUtil.nullToEmpty(message) + msgTmp;
            }
            if (!CodeRunStatus.FAILED.equals(codeRunStatus)) {
                codeRunStatus = CodeRunStatus.SUCCEED;
            }
        }
        super.onNext(frame);
    }
}

