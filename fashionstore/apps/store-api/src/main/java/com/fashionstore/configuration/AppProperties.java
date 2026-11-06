package com.fashionstore.configuration;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/** Settings under {@code fashionstore.*}; in EKS they come from the app-config ConfigMap (terraform output app_config). */
@ConfigurationProperties("fashionstore")
public record AppProperties(
        @DefaultValue("local") String version,
        @DefaultValue("ap-southeast-1") String region,
        /** "aws" (SQS/SNS) or "memory" (local runs and tests). */
        @DefaultValue("aws") String messaging,
        @DefaultValue("") String checkoutQueueUrl,
        @DefaultValue("") String statusTopicArn,
        @DefaultValue("") String dbSecretArn,
        Cognito cognito,
        Reconciler reconciler) {

    public record Cognito(String issuerUrl, String clientId, @DefaultValue("") String domain) {}

    public record Reconciler(
            @DefaultValue("true") boolean enabled,
            @DefaultValue("30") int dispatchAfterSeconds,
            @DefaultValue("30") int outcomeAfterSeconds,
            @DefaultValue("50") int batchSize) {}
}
