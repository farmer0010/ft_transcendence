package com.gyeongsan.cabinet.domain.admin.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.BDDMockito.given;

import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CabinetExportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CoinHistoryExportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.LentHistoryExportRow;
import com.gyeongsan.cabinet.domain.cabinet.model.Cabinet;
import com.gyeongsan.cabinet.domain.cabinet.model.CabinetStatus;
import com.gyeongsan.cabinet.domain.cabinet.model.LentType;
import com.gyeongsan.cabinet.domain.cabinet.port.out.CabinetRepositoryPort;
import com.gyeongsan.cabinet.domain.coin.model.CoinHistory;
import com.gyeongsan.cabinet.domain.coin.model.CoinLogType;
import com.gyeongsan.cabinet.domain.coin.port.out.CoinHistoryRepositoryPort;
import com.gyeongsan.cabinet.domain.lent.model.LentHistory;
import com.gyeongsan.cabinet.domain.lent.port.out.LentRepositoryPort;
import com.gyeongsan.cabinet.domain.user.model.User;
import com.gyeongsan.cabinet.domain.user.model.UserRole;
import java.time.LocalDateTime;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AdminDataExportServiceTest {

    @Mock private CabinetRepositoryPort cabinetRepository;
    @Mock private LentRepositoryPort lentRepository;
    @Mock private CoinHistoryRepositoryPort coinHistoryRepository;

    @InjectMocks private AdminDataExportService adminDataExportService;

    @Test
    @DisplayName("getCabinetExportRows: maps every field, enums as their name")
    void getCabinetExportRows_mapsFields() {
        Cabinet cabinet =
                Cabinet.of(9001, CabinetStatus.BROKEN, LentType.PRIVATE, 2, "note", 3, "A", 1, 2);
        given(cabinetRepository.findAll()).willReturn(List.of(cabinet));

        List<CabinetExportRow> rows = adminDataExportService.getCabinetExportRows();

        assertThat(rows).hasSize(1);
        CabinetExportRow row = rows.get(0);
        assertThat(row.visibleNum()).isEqualTo(9001);
        assertThat(row.status()).isEqualTo("BROKEN");
        assertThat(row.lentType()).isEqualTo("PRIVATE");
        assertThat(row.maxUser()).isEqualTo(2);
        assertThat(row.statusNote()).isEqualTo("note");
        assertThat(row.floor()).isEqualTo(3);
        assertThat(row.section()).isEqualTo("A");
    }

    @Test
    @DisplayName("getLentHistoryExportRows: exposes only the user's name, not email/role")
    void getLentHistoryExportRows_excludesSensitiveUserFields() {
        User user = User.of("testuser", "testuser@42gyeongsan.kr", UserRole.USER);
        Cabinet cabinet =
                Cabinet.of(9001, CabinetStatus.FULL, LentType.PRIVATE, 1, null, 1, "A", 1, 1);
        LocalDateTime start = LocalDateTime.of(2026, 1, 1, 0, 0);
        LocalDateTime end = start.plusDays(31);
        LentHistory lentHistory = LentHistory.of(user, cabinet, start, end);
        given(lentRepository.findAll()).willReturn(List.of(lentHistory));

        List<LentHistoryExportRow> rows = adminDataExportService.getLentHistoryExportRows();

        assertThat(rows).hasSize(1);
        LentHistoryExportRow row = rows.get(0);
        assertThat(row.userName()).isEqualTo("testuser");
        assertThat(row.cabinetVisibleNum()).isEqualTo(9001);
        assertThat(row.startedAt()).isEqualTo(start);
        assertThat(row.expiredAt()).isEqualTo(end);
    }

    @Test
    @DisplayName("getCoinHistoryExportRows: exposes only the user's name, not email/role")
    void getCoinHistoryExportRows_excludesSensitiveUserFields() {
        User user = User.of("coinuser", "coinuser@42gyeongsan.kr", UserRole.USER);
        CoinHistory coinHistory = CoinHistory.of(user, 100L, CoinLogType.ATTENDANCE, "출석 보상");
        given(coinHistoryRepository.findAll()).willReturn(List.of(coinHistory));

        List<CoinHistoryExportRow> rows = adminDataExportService.getCoinHistoryExportRows();

        assertThat(rows).hasSize(1);
        CoinHistoryExportRow row = rows.get(0);
        assertThat(row.userName()).isEqualTo("coinuser");
        assertThat(row.amount()).isEqualTo(100L);
        assertThat(row.type()).isEqualTo("ATTENDANCE");
        assertThat(row.description()).isEqualTo("출석 보상");
    }
}
