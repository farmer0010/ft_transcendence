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

    public Map<String, Object> predict(MultipartFile file) throws IOException {
        byte[] fileBytes = file.getBytes();
        String originalFilename = file.getOriginalFilename();

        MultipartBodyBuilder builder = new MultipartBodyBuilder();
        builder.part("file", new ByteArrayResource(fileBytes) {
            @Override
            public String getFilename() {
                return originalFilename;
            }
        }).contentType(MediaType.parseMediaType(file.getContentType()));

        @SuppressWarnings("unchecked")
        Map<String, Object> response = webClient.post()
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(BodyInserters.fromMultipartData(builder.build()))
                .retrieve()
                .bodyToMono(Map.class)
                .block();

        return response;
    }

    public String saveFile(MultipartFile file) throws IOException {
        Path uploadPath = Paths.get(resolveUploadDir(uploadDir));
        if (!Files.exists(uploadPath)) {
            Files.createDirectories(uploadPath);
        }

        String originalFilename = file.getOriginalFilename();
        String extension = "";
        if (originalFilename != null && originalFilename.contains(".")) {
            extension = originalFilename.substring(originalFilename.lastIndexOf("."));
        }
        String newFilename = "upload_" + UUID.randomUUID().toString().substring(0, 8) + extension;

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
