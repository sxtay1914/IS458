package com.fashionstore;

import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.is;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

class CartApiTest extends AbstractIntegrationTest {

    static String cart(String json) {
        return "{\"items\":" + json + "}";
    }

    @Test
    void replaceAndReadCartWithTotals() throws Exception {
        mvc.perform(put("/api/cart").with(shopper("u1")).contentType(MediaType.APPLICATION_JSON)
                        .content(cart("[{\"sku\":\"DRS-001-M\",\"qty\":2},{\"sku\":\"BAG-001\",\"qty\":1},{\"sku\":\"DRS-001-M\",\"qty\":1}]")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items", hasSize(2)))
                .andExpect(jsonPath("$.total_cents", is(3 * 5990 + 6990)));
        mvc.perform(get("/api/cart").with(shopper("u1"))).andExpect(jsonPath("$.items", hasSize(2)));
        mvc.perform(get("/api/cart").with(shopper("u2"))).andExpect(jsonPath("$.items", hasSize(0)));
    }

    @Test
    void rejectsBadItems() throws Exception {
        mvc.perform(put("/api/cart").with(shopper("u1")).contentType(MediaType.APPLICATION_JSON)
                .content(cart("[{\"sku\":\"NOPE\",\"qty\":1}]")))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.error", is("UNKNOWN_SKU")));
        mvc.perform(put("/api/cart").with(shopper("u1")).contentType(MediaType.APPLICATION_JSON)
                .content(cart("[{\"sku\":\"BAG-001\",\"qty\":0}]")))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.error", is("INVALID_REQUEST")));
        mvc.perform(put("/api/cart").with(shopper("u1")).contentType(MediaType.APPLICATION_JSON)
                .content(cart("[{\"sku\":\"BAG-001\",\"qty\":15},{\"sku\":\"BAG-001\",\"qty\":15}]")))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.error", is("QTY_LIMIT")));
    }
}
