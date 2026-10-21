package com.gyeongsan.cabinet.adapter.in.web.admin.dto.data;

/**
 * Raw, unvalidated shape read from the uploaded JSON/CSV file. status/lentType are kept as String
 * (not the enum) so an invalid value is a validation error with a clear message instead of a
 * deserialization failure.
 */
public record CabinetImportRow(
        Integer visibleNum,
        String status,
        String lentType,
        Integer maxUser,
        String statusNote,
        Integer floor,
        String section,
        Integer row,
        Integer col) {}
