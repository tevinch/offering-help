package dev.tevinch.examples.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(proxyBeanMethods = false)
public class GatewayExample {

    public static void main(String[] args) {
        SpringApplication.run(GatewayExample.class, args);
    }
}
