package com.locker.webapp.controller;

import com.locker.webapp.service.PredictionService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@Controller
public class UploadController {

    private final PredictionService predictionService;

    public UploadController(PredictionService predictionService) {
        this.predictionService = predictionService;
    }

    /**
     * 메인 업로드 페이지
     */
    @GetMapping("/")
    public String index() {
        return "index";
    }

    /**
     * 파일 업로드 처리
     */
    @PostMapping("/upload")
    public String upload(@RequestParam("file") MultipartFile file, Model model) {
        if (file.isEmpty()) {
            model.addAttribute("error", "파일을 선택해주세요.");
            return "index";
        }

        // 이미지 파일 검증
        String contentType = file.getContentType();
        if (contentType == null || !contentType.startsWith("image/")) {
            model.addAttribute("error", "이미지 파일만 업로드 가능합니다.");
            return "index";
        }

        try {
            // 1. 예측 API 호출
            Map<String, Object> prediction = predictionService.predict(file);

            // 2. 파일 저장
            String savedFilename = predictionService.saveFile(file);

            // 3. 결과를 모델에 추가
            model.addAttribute("prediction", prediction);
            model.addAttribute("savedFilename", savedFilename);
            model.addAttribute("originalFilename", file.getOriginalFilename());
            model.addAttribute("success", true);

        } catch (Exception e) {
            model.addAttribute("error", "처리 중 오류가 발생했습니다: " + e.getMessage());
            e.printStackTrace();
        }

        return "index";
    }
}
