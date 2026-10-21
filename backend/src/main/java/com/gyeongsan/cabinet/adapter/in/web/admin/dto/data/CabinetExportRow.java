package com.gyeongsan.cabinet.adapter.in.web.admin.dto.data;

public record CabinetExportRow(
        Long id,
        Integer visibleNum,
        String status,
        String lentType,
        Integer maxUser,
        String statusNote,
        Integer floor,
        String section,
        Integer row,
        Integer col) {}
