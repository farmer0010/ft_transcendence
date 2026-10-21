package com.gyeongsan.cabinet.domain.admin.port.in;

import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CabinetImportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.ImportResult;
import java.util.List;

public interface AdminDataImportUseCase {

    ImportResult importCabinets(List<CabinetImportRow> rows);
}
