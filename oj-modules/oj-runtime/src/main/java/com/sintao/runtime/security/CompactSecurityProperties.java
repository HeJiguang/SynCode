package com.sintao.runtime.security;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Component
@ConfigurationProperties(prefix = "syncode.runtime.security")
public class CompactSecurityProperties {

    private List<String> publicPaths = new ArrayList<>(List.of(
            "/actuator/health",
            "/system/sysUser/login",
            "/friend/user/sendCode",
            "/friend/user/code/login",
            "/friend/question/semiLogin/**",
            "/friend/exam/semiLogin/**",
            "/friend/message/semiLogin/**"
    ));

    public List<String> getPublicPaths() {
        return publicPaths;
    }

    public void setPublicPaths(List<String> publicPaths) {
        this.publicPaths = publicPaths;
    }
}
