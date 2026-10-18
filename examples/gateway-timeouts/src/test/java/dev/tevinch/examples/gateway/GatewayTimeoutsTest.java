package dev.tevinch.examples.gateway;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.junit.jupiter.api.parallel.Execution;
import org.junit.jupiter.api.parallel.ExecutionMode;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.context.properties.bind.Bindable;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.context.properties.source.MapConfigurationPropertySource;
import org.springframework.cloud.gateway.config.GatewayProperties;
import org.springframework.cloud.gateway.config.HttpClientProperties;
import org.springframework.cloud.gateway.route.Route;
import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.context.ConfigurableApplicationContext;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@Execution(ExecutionMode.SAME_THREAD)
@Timeout(30)
class GatewayTimeoutsTest {

    private static final Duration GLOBAL_RESPONSE_TIMEOUT = Duration.ofSeconds(1);
    private static final int CHUNK_SIZE = 64 * 1024;
    private static final int LARGE_CHUNKS = 128;
    private static final long LARGE_BYTES = 8L * 1024 * 1024;
    // SHA-256 of the 8 MiB sequence whose byte at offset i is i % 251.
    private static final String LARGE_SHA256 =
            "bdf23837181f5808331800c1ae2b4f7d7a839536b10d58491471c50dde23833a";
    private static final byte[] SHORT_BODY = "upstream complete\n".getBytes(StandardCharsets.UTF_8);
    private static final byte[] GAP_FIRST = "first\n".getBytes(StandardCharsets.UTF_8);
    private static final byte[] GAP_LAST = "last\n".getBytes(StandardCharsets.UTF_8);

    private static final Map<String, RequestRecord> REQUESTS = new ConcurrentHashMap<>();
    private static HttpServer upstream;
    private static ExecutorService upstreamExecutor;
    private static ConfigurableApplicationContext gateway;
    private static HttpClient client;
    private static URI gatewayUri;

    @BeforeAll
    static void startLocalServers() throws Exception {
        upstream = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        upstreamExecutor = Executors.newFixedThreadPool(4, task -> {
            Thread thread = new Thread(task, "example-upstream");
            thread.setDaemon(true);
            return thread;
        });
        upstream.setExecutor(upstreamExecutor);
        upstream.createContext("/", GatewayTimeoutsTest::serveUpstream);
        upstream.start();

        gateway = new SpringApplicationBuilder(GatewayExample.class)
                .web(WebApplicationType.REACTIVE)
                .logStartupInfo(false)
                .registerShutdownHook(false)
                .run("--server.port=0", "--server.address=127.0.0.1",
                        "--example.upstream-uri=http://127.0.0.1:" + upstream.getAddress().getPort(),
                        "--spring.main.banner-mode=off", "--logging.level.root=ERROR");
        int port = gateway.getEnvironment().getRequiredProperty("local.server.port", Integer.class);
        gatewayUri = URI.create("http://127.0.0.1:" + port);
        client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(2))
                .followRedirects(HttpClient.Redirect.NEVER)
                .build();

        ObservedResponse warmup = get("/default/fast", "warmup");
        assertEquals(200, warmup.status());
        assertEquals(SHORT_BODY.length, warmup.bytes());
        assertEquals(sha256(SHORT_BODY), warmup.sha256());
    }

    @AfterAll
    static void stopLocalServers() {
        if (client != null) {
            client.close();
        }
        if (gateway != null) {
            gateway.close();
        }
        if (upstream != null) {
            upstream.stop(0);
        }
        if (upstreamExecutor != null) {
            upstreamExecutor.shutdownNow();
        }
    }

    @Test
    void currentYamlBindsGlobalTimeoutsAndRouteMetadata() {
        HttpClientProperties properties = gateway.getBean(HttpClientProperties.class);
        assertEquals(Integer.valueOf(1000), properties.getConnectTimeout(),
                "The current YAML prefix must bind the connection timeout");
        assertEquals(GLOBAL_RESPONSE_TIMEOUT, properties.getResponseTimeout(),
                "The current YAML prefix must bind the response Duration");
        assertEquals("127.0.0.1", gateway.getEnvironment().getProperty("server.address"));

        Route route = gateway.getBean(RouteLocator.class).getRoutes()
                .filter(candidate -> candidate.getId().equals("extended-response"))
                .next().block(Duration.ofSeconds(5));
        assertNotNull(route, "The configured extended route must be registered");
        assertEquals(5000L, ((Number) route.getMetadata().get("response-timeout")).longValue());
        assertEquals(750L, ((Number) route.getMetadata().get("connect-timeout")).longValue());
        assertEquals("127.0.0.1", route.getUri().getHost());
        System.out.println("Configuration: global connect=1000 ms, response=1 s; route response=5000 ms");
    }

    @Test
    void olderPrefixDoesNotBindCurrentHttpClientProperties() {
        MapConfigurationPropertySource olderProperties = new MapConfigurationPropertySource(Map.of(
                "spring.cloud.gateway.httpclient.connect-timeout", "1000",
                "spring.cloud.gateway.httpclient.response-timeout", "1s"));
        Binder binder = new Binder(List.of(olderProperties));
        assertFalse(binder.bind(GatewayProperties.PREFIX + ".httpclient",
                Bindable.of(HttpClientProperties.class)).isBound());
    }

    @Test
    void fastResponseCompletesThroughTheDefaultRoute() throws Exception {
        ObservedResponse response = get("/default/fast", "fast");
        assertEquals(200, response.status());
        assertEquals(SHORT_BODY.length, response.bytes());
        assertEquals(sha256(SHORT_BODY), response.sha256());
        assertCompletedUpstream("fast", 1);
    }

    @Test
    void slowHeadersExceedingTheGlobalBudgetReturn504() throws Exception {
        ObservedResponse response = get("/default/slow-headers", "slow-default");
        assertEquals(504, response.status());
        RequestRecord record = requireRecord("slow-default");
        assertEquals(1, record.requests.get(), "A real upstream request must have started");
        assertTrue(response.total().compareTo(Duration.ofMillis(500)) >= 0);
        assertTrue(response.total().compareTo(Duration.ofSeconds(5)) < 0,
                "This must be a Gateway response, not the client's request deadline");
        assertTrue(record.finished.await(3, TimeUnit.SECONDS), "The delayed upstream attempt must finish");
        assertDelayedHeaders(record);
        printResponse("Slow headers with global budget", response);
    }

    @Test
    void longerRouteBudgetAllowsTheSameSlowHeadersAndCompleteBody() throws Exception {
        ObservedResponse response = get("/extended/slow-headers", "slow-extended");
        assertEquals(200, response.status());
        assertEquals(SHORT_BODY.length, response.bytes());
        assertEquals(sha256(SHORT_BODY), response.sha256());
        assertTrue(response.headers().compareTo(GLOBAL_RESPONSE_TIMEOUT) > 0);
        assertCompletedUpstream("slow-extended", 1);
        assertDelayedHeaders(requireRecord("slow-extended"));
        printResponse("Slow headers with route override", response);
    }

    @Test
    void eightMiBBodyCompletesEvenWhenItsTransferExceedsTheHeaderBudget() throws Exception {
        ObservedResponse response = get("/default/large", "large");
        assertEquals(200, response.status());
        assertEquals(LARGE_BYTES, response.bytes());
        assertEquals(LARGE_SHA256, response.sha256());
        assertTrue(response.total().compareTo(GLOBAL_RESPONSE_TIMEOUT) > 0);
        assertCompletedUpstream("large", LARGE_CHUNKS);
        printResponse("Complete 8 MiB stream", response);
    }

    @Test
    void bodyGapLongerThanTheHeaderBudgetStillDeliversTheFinalBytes() throws Exception {
        ObservedResponse response = get("/default/body-gap", "gap");
        assertEquals(200, response.status());
        assertEquals(11L, response.bytes());
        assertEquals(sha256("first\nlast\n".getBytes(StandardCharsets.UTF_8)), response.sha256());
        assertTrue(response.total().compareTo(GLOBAL_RESPONSE_TIMEOUT) > 0);
        assertCompletedUpstream("gap", 2);
        RequestRecord record = requireRecord("gap");
        assertTrue(Duration.ofNanos(record.lastBodyNanos - record.firstBodyNanos)
                .compareTo(GLOBAL_RESPONSE_TIMEOUT) > 0,
                "The upstream must actually leave a body gap longer than the configured budget");
        printResponse("Complete body after a 1.8 s gap", response);
    }

    private static ObservedResponse get(String path, String requestId) throws Exception {
        HttpRequest request = HttpRequest.newBuilder(gatewayUri.resolve(path + "?case=" + requestId))
                .timeout(Duration.ofSeconds(12)).GET().build();
        long start = System.nanoTime();
        HttpResponse<InputStream> response = client.send(request, HttpResponse.BodyHandlers.ofInputStream());
        Duration headers = Duration.ofNanos(System.nanoTime() - start);
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        long count = 0;
        try (InputStream body = response.body()) {
            byte[] buffer = new byte[16 * 1024];
            int read;
            while ((read = body.read(buffer)) != -1) {
                digest.update(buffer, 0, read);
                count += read;
            }
        }
        return new ObservedResponse(response.statusCode(), count, HexFormat.of().formatHex(digest.digest()),
                headers, Duration.ofNanos(System.nanoTime() - start));
    }

    private static void serveUpstream(HttpExchange exchange) throws IOException {
        String key = exchange.getRequestURI().getRawQuery();
        RequestRecord record = REQUESTS.computeIfAbsent(key, ignored -> new RequestRecord());
        record.requests.incrementAndGet();
        try {
            switch (exchange.getRequestURI().getPath()) {
                case "/fast" -> sendShortBody(exchange, record);
                case "/slow-headers" -> {
                    Thread.sleep(2500);
                    sendShortBody(exchange, record);
                }
                case "/large" -> {
                    exchange.getResponseHeaders().set("Content-Type", "application/octet-stream");
                    record.headersAttemptNanos = System.nanoTime();
                    exchange.sendResponseHeaders(200, 0);
                    try (OutputStream body = exchange.getResponseBody()) {
                        for (int chunk = 0; chunk < LARGE_CHUNKS; chunk++) {
                            byte[] bytes = new byte[CHUNK_SIZE];
                            for (int i = 0; i < bytes.length; i++) {
                                bytes[i] = (byte) ((chunk * CHUNK_SIZE + i) % 251);
                            }
                            body.write(bytes);
                            body.flush();
                            record.chunkWritten();
                            if (chunk + 1 < LARGE_CHUNKS) {
                                Thread.sleep(25);
                            }
                        }
                    }
                }
                case "/body-gap" -> {
                    record.headersAttemptNanos = System.nanoTime();
                    exchange.sendResponseHeaders(200, 0);
                    try (OutputStream body = exchange.getResponseBody()) {
                        body.write(GAP_FIRST);
                        body.flush();
                        record.chunkWritten();
                        Thread.sleep(1800);
                        body.write(GAP_LAST);
                        body.flush();
                        record.chunkWritten();
                    }
                }
                default -> exchange.sendResponseHeaders(404, -1);
            }
        }
        catch (InterruptedException error) {
            record.failure.set(error);
            Thread.currentThread().interrupt();
        }
        catch (IOException | RuntimeException error) {
            // A timed-out gateway may close its upstream connection before the delayed response.
            record.failure.set(error);
        }
        finally {
            exchange.close();
            record.finished.countDown();
        }
    }

    private static void sendShortBody(HttpExchange exchange, RequestRecord record) throws IOException {
        record.headersAttemptNanos = System.nanoTime();
        exchange.sendResponseHeaders(200, SHORT_BODY.length);
        try (OutputStream body = exchange.getResponseBody()) {
            body.write(SHORT_BODY);
            body.flush();
            record.chunkWritten();
        }
    }

    private static RequestRecord requireRecord(String requestId) {
        RequestRecord record = REQUESTS.get("case=" + requestId);
        assertNotNull(record, "The intended local upstream handler must have run");
        return record;
    }

    private static void assertCompletedUpstream(String requestId, int chunks) throws InterruptedException {
        RequestRecord record = requireRecord(requestId);
        assertTrue(record.finished.await(2, TimeUnit.SECONDS), "The whole upstream response must complete");
        assertEquals(1, record.requests.get());
        assertEquals(chunks, record.chunks.get());
        assertNull(record.failure.get(), "The upstream must finish without a hidden write error");
    }

    private static void assertDelayedHeaders(RequestRecord record) {
        assertTrue(record.headersAttemptNanos > 0, "The upstream must attempt to send delayed headers");
        assertTrue(Duration.ofNanos(record.headersAttemptNanos - record.startedNanos)
                .compareTo(Duration.ofSeconds(2)) >= 0,
                "The upstream must actually delay its headers beyond the global budget");
    }

    private static String sha256(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }

    private static void printResponse(String label, ObservedResponse response) {
        System.out.printf("%s: status=%d, bytes=%d, headers=%d ms, complete=%d ms, sha256=%s%n",
                label, response.status(), response.bytes(), response.headers().toMillis(),
                response.total().toMillis(), response.sha256());
    }

    private record ObservedResponse(int status, long bytes, String sha256, Duration headers, Duration total) {
    }

    private static final class RequestRecord {
        final long startedNanos = System.nanoTime();
        final AtomicInteger requests = new AtomicInteger();
        final AtomicInteger chunks = new AtomicInteger();
        final AtomicReference<Exception> failure = new AtomicReference<>();
        final CountDownLatch finished = new CountDownLatch(1);
        volatile long headersAttemptNanos;
        volatile long firstBodyNanos;
        volatile long lastBodyNanos;

        void chunkWritten() {
            long now = System.nanoTime();
            if (chunks.getAndIncrement() == 0) {
                firstBodyNanos = now;
            }
            lastBodyNanos = now;
        }
    }
}
