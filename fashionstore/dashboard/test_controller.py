from unittest.mock import patch

import boto3
from botocore.stub import Stubber

from controller import TestController as Controller


def test_canary_update_uses_supported_elbv2_operation():
    client = boto3.client(
        "elbv2", region_name="ap-southeast-1",
        aws_access_key_id="test", aws_secret_access_key="test",
    )
    controller = Controller()
    controller._tf_outputs = {"target_group_arns": {"v1": "target-v1", "v2": "target-v2"}}
    expected = {
        "RuleArn": "listener-rule",
        "Actions": [{
            "Type": "forward",
            "ForwardConfig": {
                "TargetGroups": [
                    {"TargetGroupArn": "target-v1", "Weight": 80},
                    {"TargetGroupArn": "target-v2", "Weight": 20},
                ],
                "TargetGroupStickinessConfig": {"Enabled": False, "DurationSeconds": 1},
            },
        }],
    }
    with Stubber(client) as stubber:
        stubber.add_response("modify_rule", {"Rules": []}, expected)
        with patch("boto3.client", return_value=client), patch.object(
            controller, "get_canary_weights", return_value={"rule_arn": "listener-rule"}
        ):
            result = controller.set_canary_weights(80, 20)
        assert result["success"], result["message"]
        stubber.assert_no_pending_responses()
