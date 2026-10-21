package com.gyeongsan.cabinet.adapter.in.web.admin.dto.data;

import java.util.List;

/**
 * Import policy is all-or-nothing: every row is validated first, and if any row fails nothing is
 * persisted (successCount is then 0). errors lists every failing row, not just the first, so the
 * whole file can be fixed in one pass.
 */
public record ImportResult(
        int totalRows, int successCount, int failureCount, List<RowError> errors) {

    public static ImportResult success(int totalRows) {
        return new ImportResult(totalRows, totalRows, 0, List.of());
    }

    public static ImportResult failure(int totalRows, List<RowError> errors) {
        return new ImportResult(totalRows, 0, errors.size(), errors);
    }
}
