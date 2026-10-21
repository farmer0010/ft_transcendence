package com.gyeongsan.cabinet.adapter.out.external.slack;

import com.gyeongsan.cabinet.alarm.dto.AlarmEvent;
import com.gyeongsan.cabinet.domain.alarm.port.out.AlarmPort;
import lombok.RequiredArgsConstructor;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Component;

/**
 * Publishes an AlarmEvent instead of calling Slack directly. The actual Slack call now happens in
 * notification-service, which consumes the resulting Redis Stream entry (see AlarmEventHandler).
 */
@Component
@RequiredArgsConstructor
public class SlackAlarmAdapter implements AlarmPort {

    private final ApplicationEventPublisher eventPublisher;

    @Override
    public void sendDm(String intraId, String message) {
        eventPublisher.publishEvent(new AlarmEvent(intraId, null, message));
    }
}
