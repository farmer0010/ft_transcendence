package com.gyeongsan.cabinet.domain.admin.port.in;

import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CabinetExportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CoinHistoryExportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.LentHistoryExportRow;
import java.util.List;

public interface AdminDataExportUseCase {

    List<CabinetExportRow> getCabinetExportRows();

    List<LentHistoryExportRow> getLentHistoryExportRows();

    List<CoinHistoryExportRow> getCoinHistoryExportRows();
}
