package com.sintao.common.message.util;

import javax.mail.Authenticator;
import javax.mail.Message;
import javax.mail.MessagingException;
import javax.mail.PasswordAuthentication;
import javax.mail.Session;
import javax.mail.Transport;
import javax.mail.internet.InternetAddress;
import javax.mail.internet.MimeMessage;
import java.security.SecureRandom;
import java.util.Date;
import java.util.Properties;

public final class MailUtils {

    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    private MailUtils() {
    }

    public static String achieveCode() {
        return Integer.toString(SECURE_RANDOM.nextInt(900_000) + 100_000);
    }

    public static void sendMail(
            String host,
            Integer port,
            String username,
            String password,
            String from,
            String subject,
            boolean auth,
            boolean startTls,
            boolean startTlsRequired,
            boolean sslEnable,
            String sslProtocols,
            String email,
            String code
    ) throws MessagingException {
        Properties props = new Properties();
        props.put("mail.smtp.auth", String.valueOf(auth));
        props.put("mail.smtp.host", host);
        props.put("mail.smtp.port", String.valueOf(port));
        props.put("mail.smtp.starttls.enable", String.valueOf(startTls));
        props.put("mail.smtp.starttls.required", String.valueOf(startTlsRequired));
        props.put("mail.smtp.ssl.enable", String.valueOf(sslEnable));
        props.put("mail.smtp.ssl.protocols", sslProtocols);
        props.put("mail.user", username);
        props.put("mail.password", password);

        Authenticator authenticator = new Authenticator() {
            @Override
            protected PasswordAuthentication getPasswordAuthentication() {
                return new PasswordAuthentication(username, password);
            }
        };

        Session mailSession = Session.getInstance(props, authenticator);
        MimeMessage message = new MimeMessage(mailSession);
        String fromAddress = (from == null || from.isBlank() || !from.contains("@")) ? username : from;

        message.setFrom(new InternetAddress(fromAddress));
        message.setRecipient(Message.RecipientType.TO, new InternetAddress(email));
        message.setSubject(subject);
        message.setSentDate(new Date());
        message.setContent(
                "尊敬的用户：您好！<br/>您的验证码为：<b>" + code
                        + "</b><br/>有效期为 5 分钟，请勿告知他人。",
                "text/html;charset=UTF-8"
        );

        Transport.send(message);
    }
}
