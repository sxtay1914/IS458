package com.fashionstore.messaging;

import com.fashionstore.configuration.AppProperties;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.services.sns.SnsClient;
import software.amazon.awssdk.services.sns.model.MessageAttributeValue;

@Component
@ConditionalOnProperty(name = "fashionstore.messaging", havingValue = "aws", matchIfMissing = true)
public class SnsOutcomePublisher implements OutcomePublisher {

    private final SnsClient sns;
    private final String topicArn;

    public SnsOutcomePublisher(SnsClient sns, AppProperties props) {
        this.sns = sns;
        this.topicArn = props.statusTopicArn();
    }

    @Override
    public void publish(String checkoutId, String status, String eventJson) {
        sns.publish(r -> r.topicArn(topicArn).message(eventJson).messageAttributes(Map.of(
                "status", MessageAttributeValue.builder().dataType("String").stringValue(status).build())));
    }
}
