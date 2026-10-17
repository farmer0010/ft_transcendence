package com.locker.webapp.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.UUID;

@Service
public class PredictionService {

    private final WebClient webClient;
    private final String uploadDir;

    public PredictionService(
            @Value("${prediction.api.url}") String predictionApiUrl,
            @Value("${upload.dir}") String uploadDir) {
        this.webClient = WebClient.builder()
                .baseUrl(predictionApiUrl)
                .build();
        this.uploadDir = uploadDir;
    }

    /**
     * 이미지를 예측 API로 전송하고 결과를 반환
     */
    public Map<String, Object> predict(MultipartFile file) throws IOException {
        byte[] fileBytes = file.getBytes();
        String originalFilename = file.getOriginalFilename();

        // Multipart 요청 구성
        MultipartBodyBuilder builder = new MultipartBodyBuilder();
        builder.part("file", new ByteArrayResource(fileBytes) {
            @Override
            public String getFilename() {
                return originalFilename;
            }
        }).contentType(MediaType.parseMediaType(file.getContentType()));

        // FastAPI 서버로 POST 요청
        @SuppressWarnings("unchecked")
        Map<String, Object> response = webClient.post()
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(BodyInserters.fromMultipartData(builder.build()))
                .retrieve()
                .bodyToMono(Map.class)
                .block();

        return response;
    }

    /**
     * 업로드된 파일을 data/test 폴더에 저장
     */
    public String saveFile(MultipartFile file) throws IOException {
        // 디렉토리 생성 (없는 경우)
        Path uploadPath = Paths.get(resolveUploadDir(uploadDir));
        if (!Files.exists(uploadPath)) {
            Files.createDirectories(uploadPath);
        }

        // 고유한 파일명 생성
        String originalFilename = file.getOriginalFilename();
        String extension = "";
        if (originalFilename != null && originalFilename.contains(".")) {
            extension = originalFilename.substring(originalFilename.lastIndexOf("."));
        }
        String newFilename = "upload_" + UUID.randomUUID().toString().substring(0, 8) + extension;

        // 파일 저장
        Path filePath = uploadPath.resolve(newFilename);
        Files.write(filePath, file.getBytes());

        return newFilename;
    }

    private String resolveUploadDir(String dir) {
        if (dir == null || dir.isBlank()) {
            return dir;
        }
        if (dir.startsWith("~")) {
            String home = System.getProperty("user.home");
            return home + dir.substring(1);
        }
        return dir;
    }
}
