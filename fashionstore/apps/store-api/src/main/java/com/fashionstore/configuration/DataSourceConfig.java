package com.fashionstore.configuration;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.secretsmanager.SecretsManagerClient;

/**
 * When DB_SECRET_ARN is set (EKS), the username and password come from the
 * RDS-managed Secrets Manager secret instead of configuration.
 */
@Configuration
@ConditionalOnExpression("!'${fashionstore.db-secret-arn:}'.isEmpty()")
public class DataSourceConfig {

    @Bean
    @ConfigurationProperties("spring.datasource.hikari")
    HikariDataSource dataSource(DataSourceProperties props, AppProperties app, ObjectMapper mapper) throws Exception {
        try (SecretsManagerClient sm = SecretsManagerClient.builder()
                .region(Region.of(app.region()))
                .httpClientBuilder(UrlConnectionHttpClient.builder())
                .build()) {
            String json = sm.getSecretValue(r -> r.secretId(app.dbSecretArn())).secretString();
            JsonNode secret = mapper.readTree(json);
            return props.initializeDataSourceBuilder()
                    .type(HikariDataSource.class)
                    .username(secret.get("username").asText())
                    .password(secret.get("password").asText())
                    .build();
        }
    }
}
