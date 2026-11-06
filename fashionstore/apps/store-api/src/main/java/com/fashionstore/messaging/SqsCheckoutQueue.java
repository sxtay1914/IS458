package com.fashionstore.messaging;

import com.fashionstore.configuration.AppProperties;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.services.sqs.SqsClient;

@Component
@ConditionalOnProperty(name = "fashionstore.messaging", havingValue = "aws", matchIfMissing = true)
public class SqsCheckoutQueue implements CheckoutQueue {

    private final SqsClient sqs;
    private final String queueUrl;

    public SqsCheckoutQueue(SqsClient sqs, AppProperties props) {
        this.sqs = sqs;
        this.queueUrl = props.checkoutQueueUrl();
    }

    @Override
    public void send(String checkoutId, String messageJson) {
        sqs.sendMessage(r -> r.queueUrl(queueUrl).messageBody(messageJson));
    }
}
