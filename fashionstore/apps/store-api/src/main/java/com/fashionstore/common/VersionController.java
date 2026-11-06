package com.fashionstore.common;

import com.fashionstore.configuration.AppProperties;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/** Which pilot version served the request: used to measure the v1/v2 weighted split. */
@RestController
public class VersionController {

    private final AppProperties props;

    public VersionController(AppProperties props) {
        this.props = props;
    }

    @GetMapping("/api/version")
    Map<String, String> version() {
        return Map.of("version", props.version());
    }
}
