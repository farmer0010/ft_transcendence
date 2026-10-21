package com.gyeongsan.cabinet.common.logging;

import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * Puts a per-request trace ID into MDC so it shows up as a field on every structured log line
 * emitted while handling this request (see logback-spring.xml's LOGSTASH appender), and echoes it
 * back as a response header so a client-reported trace ID can be correlated across services.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class TraceIdFilter implements Filter {

    private static final String HEADER_NAME = "X-Trace-Id";
    private static final String MDC_KEY = "traceId";

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        String traceId = UUID.randomUUID().toString();
        if (request instanceof jakarta.servlet.http.HttpServletRequest httpRequest) {
            String incoming = httpRequest.getHeader(HEADER_NAME);
            if (incoming != null && !incoming.isBlank()) {
                traceId = incoming;
            }
        }

        MDC.put(MDC_KEY, traceId);
        if (response instanceof HttpServletResponse httpResponse) {
            httpResponse.setHeader(HEADER_NAME, traceId);
        }

        try {
            chain.doFilter(request, response);
        } finally {
            MDC.remove(MDC_KEY);
        }
    }
}
