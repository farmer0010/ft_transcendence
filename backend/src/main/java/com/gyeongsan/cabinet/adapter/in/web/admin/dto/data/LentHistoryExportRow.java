package com.gyeongsan.cabinet.adapter.in.web.admin.dto.data;

import java.time.LocalDateTime;

/** User-identifying fields are limited to the intra name; no tokens/email/role are exported. */
public record LentHistoryExportRow(
        Long id,
        Integer cabinetVisibleNum,
        String userName,
        LocalDateTime startedAt,
        LocalDateTime expiredAt,
        LocalDateTime endedAt,
        boolean autoExtension) {}
