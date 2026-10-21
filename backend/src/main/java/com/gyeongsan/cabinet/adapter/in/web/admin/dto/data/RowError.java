package com.gyeongsan.cabinet.adapter.in.web.admin.dto.data;

/** row is 1-based and counts header-excluded data rows. */
public record RowError(int row, String field, String message) {}
