package com.fashionstore;

import java.util.TimeZone;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@ConfigurationPropertiesScan
public class StoreApiApplication {

    public static void main(String[] args) {
        // All timestamps are UTC end to end (RDS parameter group time_zone=UTC).
        TimeZone.setDefault(TimeZone.getTimeZone("UTC"));
        SpringApplication.run(StoreApiApplication.class, args);
    }
}
