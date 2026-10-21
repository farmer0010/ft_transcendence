package com.gyeongsan.cabinet.adapter.in.web.admin;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.csv.CsvMapper;
import com.fasterxml.jackson.dataformat.csv.CsvSchema;
import com.fasterxml.jackson.dataformat.xml.XmlMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CabinetExportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CabinetExportXml;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CabinetImportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CoinHistoryExportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.CoinHistoryExportXml;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.ExportFormat;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.ImportResult;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.LentHistoryExportRow;
import com.gyeongsan.cabinet.adapter.in.web.admin.dto.data.LentHistoryExportXml;
import com.gyeongsan.cabinet.common.ApiResponse;
import com.gyeongsan.cabinet.domain.admin.port.in.AdminDataExportUseCase;
import com.gyeongsan.cabinet.domain.admin.port.in.AdminDataImportUseCase;
import com.gyeongsan.cabinet.global.exception.ErrorCode;
import com.gyeongsan.cabinet.global.exception.ServiceException;
import io.github.resilience4j.ratelimiter.annotation.RateLimiter;
import java.io.IOException;
import java.io.OutputStream;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

/**
 * Admin-only bulk data export/import. Export streams the response body directly (no intermediate
 * in-memory buffer of the serialized payload); import validates the whole file before persisting
 * anything (see AdminDataImportService for the exact policy).
 */
@RestController
@RequestMapping("/v4/admin/data")
@RequiredArgsConstructor
@RateLimiter(name = "userApi")
public class AdminDataController {

    private final AdminDataExportUseCase adminDataExportUseCase;
    private final AdminDataImportUseCase adminDataImportUseCase;
    private final ObjectMapper objectMapper;

    @GetMapping("/export/cabinets")
    public ResponseEntity<StreamingResponseBody> exportCabinets(
            @RequestParam(defaultValue = "json") String format) {
        List<CabinetExportRow> rows = adminDataExportUseCase.getCabinetExportRows();
        return streamExport(
                ExportFormat.from(format),
                "cabinets",
                CabinetExportRow.class,
                rows,
                () -> new CabinetExportXml(rows));
    }

    @GetMapping("/export/lent-histories")
    public ResponseEntity<StreamingResponseBody> exportLentHistories(
            @RequestParam(defaultValue = "json") String format) {
        List<LentHistoryExportRow> rows = adminDataExportUseCase.getLentHistoryExportRows();
        return streamExport(
                ExportFormat.from(format),
                "lent_histories",
                LentHistoryExportRow.class,
                rows,
                () -> new LentHistoryExportXml(rows));
    }

    @GetMapping("/export/coin-histories")
    public ResponseEntity<StreamingResponseBody> exportCoinHistories(
            @RequestParam(defaultValue = "json") String format) {
        List<CoinHistoryExportRow> rows = adminDataExportUseCase.getCoinHistoryExportRows();
        return streamExport(
                ExportFormat.from(format),
                "coin_histories",
                CoinHistoryExportRow.class,
                rows,
                () -> new CoinHistoryExportXml(rows));
    }

    @PostMapping("/import/cabinets")
    public ResponseEntity<ApiResponse<ImportResult>> importCabinets(
            @RequestParam("file") MultipartFile file,
            @RequestParam(defaultValue = "json") String format) {
        if (file.isEmpty()) {
            throw new ServiceException(ErrorCode.IMPORT_FILE_EMPTY);
        }

        List<CabinetImportRow> rows = parseCabinetImportFile(file, ExportFormat.from(format));
        ImportResult result = adminDataImportUseCase.importCabinets(rows);

        HttpStatus status = result.failureCount() == 0 ? HttpStatus.OK : HttpStatus.BAD_REQUEST;
        return ResponseEntity.status(status).body(ApiResponse.success(result));
    }

    private List<CabinetImportRow> parseCabinetImportFile(MultipartFile file, ExportFormat format) {
        try {
            return switch (format) {
                case JSON ->
                        objectMapper.readValue(
                                file.getInputStream(),
                                new TypeReference<List<CabinetImportRow>>() {});
                case CSV -> {
                    CsvMapper csvMapper = new CsvMapper();
                    csvMapper.registerModule(new JavaTimeModule());
                    // Bind by the file's actual header names (column order in the file may
                    // differ from the record's declaration order) rather than a schema built
                    // from the class, which would bind positionally instead.
                    CsvSchema schema = CsvSchema.emptySchema().withHeader();
                    yield csvMapper
                            .readerFor(CabinetImportRow.class)
                            .with(schema)
                            .<CabinetImportRow>readValues(file.getInputStream())
                            .readAll();
                }
                case XML -> throw new ServiceException(ErrorCode.INVALID_EXPORT_FORMAT);
            };
        } catch (IOException e) {
            throw new ServiceException(ErrorCode.IMPORT_FILE_PARSE_FAILED);
        }
    }

    private <T> ResponseEntity<StreamingResponseBody> streamExport(
            ExportFormat format,
            String fileBaseName,
            Class<T> rowType,
            List<T> rows,
            java.util.function.Supplier<Object> xmlWrapperSupplier) {
        MediaType mediaType;
        String extension;
        StreamingResponseBody body;

        switch (format) {
            case JSON -> {
                mediaType = MediaType.APPLICATION_JSON;
                extension = "json";
                body = out -> objectMapper.writeValue(out, rows);
            }
            case CSV -> {
                mediaType = new MediaType("text", "csv");
                extension = "csv";
                body = out -> writeCsv(rows, rowType, out);
            }
            case XML -> {
                mediaType = MediaType.APPLICATION_XML;
                extension = "xml";
                body = out -> writeXml(xmlWrapperSupplier.get(), out);
            }
            default -> throw new ServiceException(ErrorCode.INVALID_EXPORT_FORMAT);
        }

        return ResponseEntity.ok()
                .contentType(mediaType)
                .header(
                        HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"" + fileBaseName + "." + extension + "\"")
                .body(body);
    }

    private <T> void writeCsv(List<T> rows, Class<T> rowType, OutputStream out) throws IOException {
        CsvMapper csvMapper = new CsvMapper();
        csvMapper.registerModule(new JavaTimeModule());
        CsvSchema schema = csvMapper.schemaFor(rowType).withHeader();
        csvMapper.writer(schema).writeValue(out, rows);
    }

    private void writeXml(Object wrapper, OutputStream out) throws IOException {
        XmlMapper xmlMapper = new XmlMapper();
        xmlMapper.registerModule(new JavaTimeModule());
        xmlMapper.writeValue(out, wrapper);
    }
}
