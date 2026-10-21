package com.gyeongsan.cabinet.adapter.in.web.admin.dto.data;

import com.gyeongsan.cabinet.global.exception.ErrorCode;
import com.gyeongsan.cabinet.global.exception.ServiceException;

public enum ExportFormat {
    JSON,
    CSV,
    XML;

    public static ExportFormat from(String value) {
        try {
            return ExportFormat.valueOf(value.toUpperCase());
        } catch (IllegalArgumentException | NullPointerException e) {
            throw new ServiceException(ErrorCode.INVALID_EXPORT_FORMAT);
        }
    }
}
