package com.fashionstore.configuration;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.sns.SnsClient;
import software.amazon.awssdk.services.sqs.SqsClient;

/**
 * AWS clients. Credentials come from the default chain: on EKS that is IRSA
 * (web identity token + the store-api role), locally your AWS profile.
 */
@Configuration
@ConditionalOnProperty(name = "fashionstore.messaging", havingValue = "aws", matchIfMissing = true)
public class AwsConfig {

    @Bean(destroyMethod = "close")
    SqsClient sqsClient(AppProperties props) {
        return SqsClient.builder()
                .region(Region.of(props.region()))
                .httpClientBuilder(UrlConnectionHttpClient.builder())
                .build();
    }

    @Bean(destroyMethod = "close")
    SnsClient snsClient(AppProperties props) {
        return SnsClient.builder()
                .region(Region.of(props.region()))
                .httpClientBuilder(UrlConnectionHttpClient.builder())
                .build();
    }
}
