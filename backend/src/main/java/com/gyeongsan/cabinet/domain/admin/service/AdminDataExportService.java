package com.gyeongsan.cabinet.domain.admin.service;

import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CabinetExportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CoinHistoryExportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.LentHistoryExportRow;
import com.gyeongsan.cabinet.domain.admin.port.in.AdminDataExportUseCase;
import com.gyeongsan.cabinet.domain.cabinet.model.Cabinet;
import com.gyeongsan.cabinet.domain.cabinet.port.out.CabinetRepositoryPort;
import com.gyeongsan.cabinet.domain.coin.model.CoinHistory;
import com.gyeongsan.cabinet.domain.coin.port.out.CoinHistoryRepositoryPort;
import com.gyeongsan.cabinet.domain.lent.model.LentHistory;
import com.gyeongsan.cabinet.domain.lent.port.out.LentRepositoryPort;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Builds export rows for the admin data-export API. Mapping to the plain record types happens here,
 * inside the transaction, so lazy associations (LentHistory.user, CoinHistory.user) are resolved
 * before the Hibernate session closes rather than at HTTP-response-streaming time.
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AdminDataExportService implements AdminDataExportUseCase {

    private final CabinetRepositoryPort cabinetRepository;
    private final LentRepositoryPort lentRepository;
    private final CoinHistoryRepositoryPort coinHistoryRepository;

    @Override
    public List<CabinetExportRow> getCabinetExportRows() {
        return cabinetRepository.findAll().stream().map(this::toRow).toList();
    }

    @Override
    public List<LentHistoryExportRow> getLentHistoryExportRows() {
        return lentRepository.findAll().stream().map(this::toRow).toList();
    }

    @Override
    public List<CoinHistoryExportRow> getCoinHistoryExportRows() {
        return coinHistoryRepository.findAll().stream().map(this::toRow).toList();
    }

    private CabinetExportRow toRow(Cabinet cabinet) {
        return new CabinetExportRow(
                cabinet.getId(),
                cabinet.getVisibleNum(),
                cabinet.getStatus().name(),
                cabinet.getLentType().name(),
                cabinet.getMaxUser(),
                cabinet.getStatusNote(),
                cabinet.getFloor(),
                cabinet.getSection(),
                cabinet.getRow(),
                cabinet.getCol());
    }

    private LentHistoryExportRow toRow(LentHistory lentHistory) {
        return new LentHistoryExportRow(
                lentHistory.getId(),
                lentHistory.getCabinet().getVisibleNum(),
                lentHistory.getUser().getName(),
                lentHistory.getStartedAt(),
                lentHistory.getExpiredAt(),
                lentHistory.getEndedAt(),
                lentHistory.isAutoExtension());
    }

    private CoinHistoryExportRow toRow(CoinHistory coinHistory) {
        return new CoinHistoryExportRow(
                coinHistory.getId(),
                coinHistory.getUser().getName(),
                coinHistory.getAmount(),
                coinHistory.getType().name(),
                coinHistory.getDescription(),
                coinHistory.getCreatedAt());
    }
}
