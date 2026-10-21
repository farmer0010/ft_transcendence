package com.gyeongsan.cabinet.domain.admin.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CabinetImportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.ImportResult;
import com.gyeongsan.cabinet.domain.cabinet.model.Cabinet;
import com.gyeongsan.cabinet.domain.cabinet.model.CabinetStatus;
import com.gyeongsan.cabinet.domain.cabinet.model.LentType;
import com.gyeongsan.cabinet.domain.cabinet.port.out.CabinetRepositoryPort;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AdminDataImportServiceTest {

    @Mock private CabinetRepositoryPort cabinetRepository;

    @InjectMocks private AdminDataImportService adminDataImportService;

    @Test
    @DisplayName("importCabinets: all rows valid -> persists everything, zero errors")
    void importCabinets_allValid_persistsAll() {
        given(cabinetRepository.findAll()).willReturn(List.of());

        List<CabinetImportRow> rows =
                List.of(
                        new CabinetImportRow(9001, "AVAILABLE", "PRIVATE", 1, null, 1, "A", 1, 1),
                        new CabinetImportRow(9002, "BROKEN", "LAPISCINE", 2, "note", 2, "B", 1, 2));

        ImportResult result = adminDataImportService.importCabinets(rows);

        assertThat(result.totalRows()).isEqualTo(2);
        assertThat(result.successCount()).isEqualTo(2);
        assertThat(result.failureCount()).isZero();
        assertThat(result.errors()).isEmpty();

        ArgumentCaptor<List<Cabinet>> captor = ArgumentCaptor.forClass(List.class);
        verify(cabinetRepository).saveAll(captor.capture());
        assertThat(captor.getValue()).hasSize(2);
        assertThat(captor.getValue().get(0).getVisibleNum()).isEqualTo(9001);
    }

    @Test
    @DisplayName("importCabinets: visibleNum already exists in DB -> rejects, persists nothing")
    void importCabinets_duplicateAgainstExisting_rejectsAll() {
        Cabinet existing =
                Cabinet.of(9001, CabinetStatus.AVAILABLE, LentType.PRIVATE, 1, null, 1, "A", 1, 1);
        given(cabinetRepository.findAll()).willReturn(List.of(existing));

        List<CabinetImportRow> rows =
                List.of(new CabinetImportRow(9001, "AVAILABLE", "PRIVATE", 1, null, 1, "A", 1, 1));

        ImportResult result = adminDataImportService.importCabinets(rows);

        assertThat(result.successCount()).isZero();
        assertThat(result.failureCount()).isEqualTo(1);
        assertThat(result.errors().get(0).row()).isEqualTo(1);
        assertThat(result.errors().get(0).field()).isEqualTo("visibleNum");
        verify(cabinetRepository, never()).saveAll(org.mockito.ArgumentMatchers.any());
    }

    @Test
    @DisplayName("importCabinets: duplicate visibleNum within the file -> rejects both rows")
    void importCabinets_duplicateWithinFile_rejectsAll() {
        given(cabinetRepository.findAll()).willReturn(List.of());

        List<CabinetImportRow> rows =
                List.of(
                        new CabinetImportRow(9001, "AVAILABLE", "PRIVATE", 1, null, 1, "A", 1, 1),
                        new CabinetImportRow(9001, "BROKEN", "PRIVATE", 1, null, 1, "A", 1, 1));

        ImportResult result = adminDataImportService.importCabinets(rows);

        assertThat(result.successCount()).isZero();
        assertThat(result.failureCount()).isEqualTo(1);
        assertThat(result.errors().get(0).row()).isEqualTo(2);
        verify(cabinetRepository, never()).saveAll(org.mockito.ArgumentMatchers.any());
    }

    @Test
    @DisplayName("importCabinets: invalid status enum value -> rejects with a clear field error")
    void importCabinets_invalidStatus_rejects() {
        given(cabinetRepository.findAll()).willReturn(List.of());

        List<CabinetImportRow> rows =
                List.of(
                        new CabinetImportRow(
                                9001, "NOT_A_STATUS", "PRIVATE", 1, null, 1, "A", 1, 1));

        ImportResult result = adminDataImportService.importCabinets(rows);

        assertThat(result.failureCount()).isEqualTo(1);
        assertThat(result.errors().get(0).field()).isEqualTo("status");
        verify(cabinetRepository, never()).saveAll(org.mockito.ArgumentMatchers.any());
    }

    @Test
    @DisplayName("importCabinets: missing maxUser -> rejects with a clear field error")
    void importCabinets_missingMaxUser_rejects() {
        given(cabinetRepository.findAll()).willReturn(List.of());

        List<CabinetImportRow> rows =
                List.of(
                        new CabinetImportRow(
                                9001, "AVAILABLE", "PRIVATE", null, null, 1, "A", 1, 1));

        ImportResult result = adminDataImportService.importCabinets(rows);

        assertThat(result.failureCount()).isEqualTo(1);
        assertThat(result.errors().get(0).field()).isEqualTo("maxUser");
        verify(cabinetRepository, never()).saveAll(org.mockito.ArgumentMatchers.any());
    }

    @Test
    @DisplayName("importCabinets: mixed valid/invalid rows -> all-or-nothing, reports every error")
    void importCabinets_mixedRows_reportsAllErrorsAndPersistsNothing() {
        given(cabinetRepository.findAll()).willReturn(List.of());

        List<CabinetImportRow> rows =
                List.of(
                        new CabinetImportRow(9001, "AVAILABLE", "PRIVATE", 1, null, 1, "A", 1, 1),
                        new CabinetImportRow(
                                9002, "NOT_A_STATUS", "PRIVATE", 1, null, 1, "A", 1, 2),
                        new CabinetImportRow(
                                9003, "AVAILABLE", "NOT_A_TYPE", 1, null, 1, "A", 1, 3));

        ImportResult result = adminDataImportService.importCabinets(rows);

        assertThat(result.totalRows()).isEqualTo(3);
        assertThat(result.successCount()).isZero();
        assertThat(result.failureCount()).isEqualTo(2);
        verify(cabinetRepository, never()).saveAll(org.mockito.ArgumentMatchers.any());
    }
}
