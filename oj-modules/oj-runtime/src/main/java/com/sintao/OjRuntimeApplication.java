package com.sintao;

import com.sintao.friend.OjFriendApplication;
import com.sintao.job.OjJobApplication;
import com.sintao.system.OjSystemApplication;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.FilterType;
import org.springframework.context.annotation.FullyQualifiedAnnotationBeanNameGenerator;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootConfiguration
@EnableAutoConfiguration
@ComponentScan(
        basePackages = {
                "com.sintao.runtime",
                "com.sintao.system",
                "com.sintao.friend",
                "com.sintao.job"
        },
        nameGenerator = FullyQualifiedAnnotationBeanNameGenerator.class,
        excludeFilters = @ComponentScan.Filter(
                type = FilterType.ASSIGNABLE_TYPE,
                classes = {
                        OjSystemApplication.class,
                        OjFriendApplication.class,
                        OjJobApplication.class,
                        com.sintao.system.config.TrustedExamTimeConfig.class,
                        com.sintao.friend.config.TrustedExamTimeConfig.class,
                        com.sintao.job.config.TrustedExamTimeConfig.class
                }
        )
)
@MapperScan(
        basePackages = {
                "com.sintao.system.mapper",
                "com.sintao.system.test.mapper",
                "com.sintao.friend.mapper",
                "com.sintao.job.mapper"
        },
        nameGenerator = FullyQualifiedAnnotationBeanNameGenerator.class
)
@EnableFeignClients(basePackages = "com.sintao.api")
@EnableScheduling
public class OjRuntimeApplication {

    public static void main(String[] args) {
        SpringApplication.run(OjRuntimeApplication.class, args);
    }
}
