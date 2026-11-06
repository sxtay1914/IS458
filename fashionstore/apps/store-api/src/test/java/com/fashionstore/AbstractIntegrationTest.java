package com.fashionstore;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;

import com.fashionstore.configuration.SecurityConfig;
import com.fashionstore.messaging.InMemoryMessaging;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import javax.sql.DataSource;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.io.FileSystemResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.init.ScriptUtils;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.MySQLContainer;

/**
 * Real MySQL 8 (Testcontainers) with the canonical Flyway migrations from
 * database/migrations and the demo seeds, reset before every test.
 */
@SpringBootTest(properties = {
        "spring.flyway.enabled=false",
        "fashionstore.messaging=memory",
        "fashionstore.reconciler.enabled=false",
        "fashionstore.reconciler.dispatch-after-seconds=0",
        "fashionstore.reconciler.outcome-after-seconds=0",
        "fashionstore.cognito.issuer-url=https://cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_test",
        "fashionstore.cognito.client-id=test-client",
})
@AutoConfigureMockMvc
public abstract class AbstractIntegrationTest {

    static final Path REPO_ROOT = Path.of(System.getProperty("repo.root", "../..")).toAbsolutePath().normalize();

    @SuppressWarnings("resource")
    static final MySQLContainer<?> MYSQL = new MySQLContainer<>("mysql:8.4")
            .withDatabaseName("fashionstore").withUsername("test").withPassword("test")
            .withCommand("--default-time-zone=+00:00");

    static {
        MYSQL.start();
        Flyway.configure()
                .dataSource(MYSQL.getJdbcUrl(), MYSQL.getUsername(), MYSQL.getPassword())
                .locations("filesystem:" + REPO_ROOT.resolve("database/migrations"))
                .load().migrate();
    }

    @DynamicPropertySource
    static void datasource(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", () -> MYSQL.getJdbcUrl() + "?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true");
        r.add("spring.datasource.username", MYSQL::getUsername);
        r.add("spring.datasource.password", MYSQL::getPassword);
    }

    @Autowired protected MockMvc mvc;
    @Autowired protected JdbcTemplate db;
    @Autowired protected InMemoryMessaging messaging;
    @Autowired protected DataSource dataSource;

    @BeforeEach
    void resetDatabase() throws Exception {
        db.execute("SET FOREIGN_KEY_CHECKS = 0");
        for (String t : List.of("reconciliation_log", "notification_log", "order_items", "orders", "checkouts",
                "cart_items", "carts", "inventory", "products")) {
            db.execute("DELETE FROM " + t);
        }
        db.execute("SET FOREIGN_KEY_CHECKS = 1");
        try (var conn = dataSource.getConnection()) {
            for (String seed : List.of("products.sql", "inventory.sql")) {
                Path p = REPO_ROOT.resolve("database/seeds").resolve(seed);
                if (!Files.exists(p)) {
                    throw new IllegalStateException("seed not found: " + p);
                }
                ScriptUtils.executeSqlScript(conn, new FileSystemResource(p));
            }
        }
        messaging.reset();
    }

    /** A Cognito-style access token for {@code sub} with both API scopes. */
    protected static JwtRequestPostProcessor shopper(String sub) {
        return jwt().jwt(j -> j.subject(sub).claim("email", sub + "@example.com")
                        .claim("token_use", "access").claim("client_id", "test-client"))
                .authorities(new SimpleGrantedAuthority(SecurityConfig.SCOPE_CHECKOUT),
                        new SimpleGrantedAuthority(SecurityConfig.SCOPE_ORDERS));
    }
}
