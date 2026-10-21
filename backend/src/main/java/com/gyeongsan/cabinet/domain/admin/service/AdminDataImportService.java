package com.gyeongsan.cabinet.domain.admin.service;

import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CabinetImportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.ImportResult;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.RowError;
import com.gyeongsan.cabinet.domain.admin.port.in.AdminDataImportUseCase;
import com.gyeongsan.cabinet.domain.cabinet.model.Cabinet;
import com.gyeongsan.cabinet.domain.cabinet.model.CabinetStatus;
import com.gyeongsan.cabinet.domain.cabinet.model.LentType;
import com.gyeongsan.cabinet.domain.cabinet.port.out.CabinetRepositoryPort;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Import policy: validate every row first; if any row is invalid, persist nothing and report every
 * failing row (not just the first) so the file can be fixed in one pass. Only on a zero-error file
 * does this insert anything, in a single batch save.
 */
@Service
@RequiredArgsConstructor
public class AdminDataImportService implements AdminDataImportUseCase {

    private final CabinetRepositoryPort cabinetRepository;

    @Override
    @Transactional
    public ImportResult importCabinets(List<CabinetImportRow> rows) {
        if (rows.isEmpty()) {
            return ImportResult.success(0);
        }

        Set<Integer> existingVisibleNums =
                cabinetRepository.findAll().stream()
                        .map(Cabinet::getVisibleNum)
                        .collect(java.util.stream.Collectors.toSet());

        List<RowError> errors = new ArrayList<>();
        Set<Integer> seenInFile = new HashSet<>();
        List<Cabinet> toInsert = new ArrayList<>();

        for (int i = 0; i < rows.size(); i++) {
            int rowNumber = i + 1;
            CabinetImportRow row = rows.get(i);

            if (row.visibleNum() == null) {
                errors.add(new RowError(rowNumber, "visibleNum", "visibleNum은 필수입니다."));
                continue;
            }
            if (row.maxUser() == null || row.maxUser() <= 0) {
                errors.add(new RowError(rowNumber, "maxUser", "maxUser는 1 이상이어야 합니다."));
                continue;
            }

            CabinetStatus status = parseEnum(CabinetStatus.class, row.status());
            if (status == null) {
                errors.add(
                        new RowError(rowNumber, "status", "유효하지 않은 status 입니다: " + row.status()));
                continue;
            }

            LentType lentType = parseEnum(LentType.class, row.lentType());
            if (lentType == null) {
                errors.add(
                        new RowError(
                                rowNumber, "lentType", "유효하지 않은 lentType 입니다: " + row.lentType()));
                continue;
            }

            if (existingVisibleNums.contains(row.visibleNum())) {
                errors.add(
                        new RowError(
                                rowNumber,
                                "visibleNum",
                                "이미 존재하는 visibleNum 입니다: " + row.visibleNum()));
                continue;
            }
            if (!seenInFile.add(row.visibleNum())) {
                errors.add(
                        new RowError(
                                rowNumber,
                                "visibleNum",
                                "파일 내에 중복된 visibleNum 입니다: " + row.visibleNum()));
                continue;
            }

            toInsert.add(
                    Cabinet.of(
                            row.visibleNum(),
                            status,
                            lentType,
                            row.maxUser(),
                            row.statusNote(),
                            row.floor(),
                            row.section(),
                            row.row(),
                            row.col()));
        }

        if (!errors.isEmpty()) {
            return ImportResult.failure(rows.size(), errors);
        }

        cabinetRepository.saveAll(toInsert);
        return ImportResult.success(rows.size());
    }

    private static <E extends Enum<E>> E parseEnum(Class<E> enumType, String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Enum.valueOf(enumType, value.trim().toUpperCase());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
