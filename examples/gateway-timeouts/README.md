# Spring Cloud Gateway timeouts

A backend can accept a TCP connection quickly and still take a long time to send response headers. A large response can also take several seconds to download after its headers arrive. Those are different waits.

This example uses Spring Cloud Gateway **Server WebFlux 5.0.3**, Spring Boot **4.0.8**, Spring Cloud **2025.1.3**, and Java **21**. It demonstrates the current configuration prefix, route overrides, and complete response bodies with a local HTTP upstream.

## Choose the timeout for the wait

| Setting | Unit | What it controls in this example |
| --- | --- | --- |
| Global `httpclient.connect-timeout` | Milliseconds | Establishing the TCP connection to the upstream |
| Global `httpclient.response-timeout` | A `Duration`, such as `1s` | Waiting for the upstream response before its headers are available |
| Route metadata `connect-timeout` | Milliseconds | Connection timeout for this route |
| Route metadata `response-timeout` | Milliseconds | Response timeout for this route |

Increasing the connection timeout will not give a backend more time to compute a response after it has connected. For a known slow endpoint, use a response timeout that fits that endpoint's expected wait for headers.

In this Gateway version, the response timeout wraps the routing operation until the upstream response is available; the response body is forwarded afterward. It does not set a deadline for downloading the entire body or for a gap between body chunks. This Gateway property is also separate from Reactor Netty's `HttpClient.responseTimeout` API. If you need a whole-transfer or body-idle limit, treat that as a separate requirement.

These short values make the demonstration quick. Choose production budgets from the backend's behavior and the surrounding client and proxy deadlines.

## Configuration

The global prefix for this version is `spring.cloud.gateway.server.webflux.httpclient`:

```yaml
spring.cloud.gateway.server.webflux.httpclient:
  connect-timeout: 1000
  response-timeout: 1s

spring.cloud.gateway.server.webflux.routes:
  - id: extended-response
    uri: http://127.0.0.1:9091
    predicates:
      - Path=/extended/**
    filters:
      - StripPrefix=1
    metadata:
      connect-timeout: 750
      response-timeout: 5000
```

The route response value is **5000 milliseconds**, whereas the global response value is a **Duration**. The older `spring.cloud.gateway.httpclient` prefix does not bind these current properties. Match the configuration reference to your installed Gateway version when adapting the example.

The full [application.yml](src/main/resources/application.yml) also has a `/default/**` route that uses the global settings. Both routes remove their first path segment before forwarding.

## Run the local checks

With JDK 21 and Maven 3.6.3 or newer, run from this directory:

```sh
mvn test
```

The tests create a Gateway and a synthetic upstream on ephemeral ports bound to `127.0.0.1`. They close both servers afterward. No separately running backend is needed.

The checks cover:

- The actual application configuration binds the global values and route metadata. A separate negative check rejects the old prefix.
- A fast request returns its complete known body through the default route.
- An upstream that waits 2.5 seconds before sending headers receives a **504** through the default route's 1 second budget.
- The same delayed response returns **200** and its complete body through the route's 5000 millisecond override.
- A deterministic **8 MiB** response, streamed in **128 chunks** over more than 1 second, is consumed completely. The client checks the byte count and SHA-256, and the upstream independently records every chunk.
- A response with a **1.8 second gap** between its first and last body bytes still delivers the complete known body.

The large response's expected SHA-256 is:

```text
bdf23837181f5808331800c1ae2b4f7d7a839536b10d58491471c50dde23833a
```

The client hashes the stream as it reads it; it does not aggregate the body in Gateway or rely on a small client buffer limit. Each test method has a 30-second JUnit timeout; the local fixture uses bounded delays.

All seven checks passed with Temurin **21.0.12.1** and Maven **3.10.0**. The resolved dependencies were Gateway **5.0.3**, Boot **4.0.8**, and Reactor Netty **1.3.7**. One scripted local run produced these results; timings vary by machine:

| Scenario | Status | Received bytes | Completion time |
| --- | --- | --- | --- |
| Slow headers, global budget | 504 | Error response | 1.06 s |
| Slow headers, route override | 200 | 18 | 2.52 s |
| Complete large stream | 200 | 8,388,608 | 4.19 s |
| Complete body after a gap | 200 | 11 | 1.86 s |

This is a scripted local HTTP/1.1 example of the pinned WebFlux configuration. It does not measure a delayed TCP handshake or cover WebMVC, custom HTTP client settings, TLS, load balancer deadlines, uploads, or infinite streams. An immediately refused connection would not demonstrate an elapsed connection timeout.

## References

- [Gateway timeout configuration](https://docs.spring.io/spring-cloud-gateway/reference/spring-cloud-gateway-server-webflux/http-timeouts-configuration.html)
- [Gateway configuration properties](https://docs.spring.io/spring-cloud-gateway/reference/configprops.html)
- [Gateway 5.0.3 routing and response timeout](https://github.com/spring-cloud/spring-cloud-gateway/blob/v5.0.3/spring-cloud-gateway-server-webflux/src/main/java/org/springframework/cloud/gateway/filter/NettyRoutingFilter.java)
- [Gateway 5.0.3 response body forwarding](https://github.com/spring-cloud/spring-cloud-gateway/blob/v5.0.3/spring-cloud-gateway-server-webflux/src/main/java/org/springframework/cloud/gateway/filter/NettyWriteResponseFilter.java)
- [Spring Cloud release compatibility](https://spring.io/projects/spring-cloud/)

## Optional coffee

This example is free to use. If it saves you time and you would like to buy me a coffee, contributions are optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
