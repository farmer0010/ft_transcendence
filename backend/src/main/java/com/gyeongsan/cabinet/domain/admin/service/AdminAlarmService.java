package com.gyeongsan.cabinet.domain.admin.service;

import com.gyeongsan.cabinet.domain.admin.port.in.AdminAlarmUseCase;
import com.gyeongsan.cabinet.domain.alarm.port.out.AlarmPort;
import com.gyeongsan.cabinet.domain.lent.model.LentHistory;
import com.gyeongsan.cabinet.domain.lent.port.out.LentRepositoryPort;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.log4j.Log4j2;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Log4j2
public class AdminAlarmService implements AdminAlarmUseCase {

    private final LentRepositoryPort lentRepository;
    private final AlarmPort alarmPort;

    // AlarmPort now publishes an AlarmEvent that is picked up by an
    // AFTER_COMMIT transactional listener (see AlarmEventHandler), so this
    // needs an explicit transaction boundary for that listener to fire.
    @Override
    @Transactional(readOnly = true)
    public void sendEmergencyNotice(String message) {
        List<LentHistory> activeLents = lentRepository.findAllActiveLents();

        int successCount = 0;
        for (LentHistory lent : activeLents) {
            try {
                String intraId = lent.getUser().getName();
                alarmPort.sendDm(intraId, "[SUBAK 긴급공지] " + message);
                successCount++;
            } catch (Exception e) {
                log.error("Emergency DM send failed for user: {}", lent.getUser().getName());
            }
        }
    }
}
