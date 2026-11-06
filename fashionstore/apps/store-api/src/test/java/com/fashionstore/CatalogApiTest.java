package com.fashionstore;

import static org.hamcrest.Matchers.everyItem;
import static org.hamcrest.Matchers.greaterThan;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.is;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;

class CatalogApiTest extends AbstractIntegrationTest {

    @Test
    void catalogueIsPublicAndIncludesStock() throws Exception {
        mvc.perform(get("/api/products"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(10)))
                .andExpect(jsonPath("$[0].price_cents").isNumber())
                .andExpect(header().exists("X-Correlation-Id"));
    }

    @Test
    void filtersByCategoryAndStock() throws Exception {
        mvc.perform(get("/api/products").param("category", "dresses"))
                .andExpect(jsonPath("$", hasSize(3)))
                .andExpect(jsonPath("$[*].category", everyItem(is("dresses"))));
        db.update("UPDATE inventory SET qty = 0 WHERE sku = 'BAG-001'");
        mvc.perform(get("/api/products").param("in_stock", "true"))
                .andExpect(jsonPath("$", hasSize(9)))
                .andExpect(jsonPath("$[*].stock", everyItem(greaterThan(0))));
    }

    @Test
    void productDetailsAnd404() throws Exception {
        mvc.perform(get("/api/products/FLASH-001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.stock", is(50)))
                .andExpect(jsonPath("$.price_cents", is(9990)));
        mvc.perform(get("/api/products/NOPE"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error", is("NOT_FOUND")))
                .andExpect(jsonPath("$.correlation_id").isString());
    }

    @Test
    void correlationIdIsPropagated() throws Exception {
        mvc.perform(get("/api/products").header("X-Correlation-Id", "abc-123"))
                .andExpect(header().string("X-Correlation-Id", "abc-123"));
    }

    @Test
    void versionEndpointReportsPilotVersion() throws Exception {
        mvc.perform(get("/api/version")).andExpect(status().isOk()).andExpect(jsonPath("$.version").isString());
    }

    @Test
    void healthProbesArePublic() throws Exception {
        mvc.perform(get("/actuator/health/readiness")).andExpect(status().isOk());
        mvc.perform(get("/actuator/health/liveness")).andExpect(status().isOk());
    }
}
