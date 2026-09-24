package com.sintao.common.message.service;

import com.sintao.common.message.util.MailUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.mail.MessagingException;

@Component
@Slf4j
public class MailService implements InitializingBean {

    @Value("${mail.host:}")
    private String host;

    @Value("${mail.port:587}")
    private Integer port;

    @Value("${mail.username:}")
    private String username;

    @Value("${mail.password:}")
    private String password;

    @Value("${mail.from:}")
    private String from;

    @Value("${mail.subject:OnlineOJ 邮箱验证码}")
    private String subject;

    @Value("${mail.auth:true}")
    private boolean auth;

    @Value("${mail.starttls:true}")
    private boolean startTls;

    @Value("${mail.starttls-required:true}")
    private boolean startTlsRequired;

    @Value("${mail.ssl-enable:false}")
    private boolean sslEnable;

    @Value("${mail.ssl-protocols:TLSv1.2}")
    private String sslProtocols;

    @Value("${mail.is-send:false}")
    private boolean deliveryEnabled;

    @Override
    public void afterPropertiesSet() {
        if (!deliveryEnabled) {
            return;
        }
        if (isBlank(host) || isBlank(username) || isBlank(password)) {
            throw new IllegalStateException(
                    "mail.host, mail.username and mail.password are required when mail.is-send=true"
            );
        }
        if (port == null || port <= 0 || port > 65535) {
            throw new IllegalStateException("mail.port must be between 1 and 65535");
        }
        if (sslEnable && startTls) {
            throw new IllegalStateException("mail.ssl-enable and mail.starttls cannot both be true");
        }
    }

    public String generateCode() {
        return MailUtils.achieveCode();
    }

    public boolean sendLoginCode(String email, String code) {
        try {
            MailUtils.sendMail(
                    host,
                    port,
                    username,
                    password,
                    from,
                    subject,
                    auth,
                    startTls,
                    startTlsRequired,
                    sslEnable,
                    sslProtocols,
                    email,
                    code
            );
            return true;
        } catch (MessagingException ex) {
            log.error("send mail failed, email={}", email, ex);
            return false;
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
