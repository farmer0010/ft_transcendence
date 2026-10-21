package com.gyeongsan.cabinet.adapter.in.web.admin.dto.data;

import java.time.LocalDateTime;

/** User-identifying fields are limited to the intra name; no tokens/email/role are exported. */
public record CoinHistoryExportRow(
        Long id,
        String userName,
        Long amount,
        String type,
        String description,
        LocalDateTime createdAt) {}
