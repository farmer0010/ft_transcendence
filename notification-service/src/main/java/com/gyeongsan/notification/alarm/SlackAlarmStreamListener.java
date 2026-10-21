package com.gyeongsan.notification.alarm;

import com.gyeongsan.notification.config.RedisStreamConfig;
import java.time.Duration;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.stream.StreamListener;
import org.springframework.stereotype.Component;

/**
 * Consumes the Slack alarm stream and sends the DM. Logic matches the
 * listener that used to run inside the backend, with one addition: a
 * dedup guard keyed by the stream record ID, so a redelivered message
 * (e.g. after a crash before ack) does not result in a duplicate Slack
 * message being sent.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class SlackAlarmStreamListener
        implements StreamListener<String, MapRecord<String, String, String>> {

    private static final String DEDUP_KEY_PREFIX = "notification:processed:";
    private static final Duration DEDUP_TTL = Duration.ofHours(24);

    private final SlackBotService slackBotService;
    private final RedisTemplate<String, Object> redisTemplate;
    private final StringRedisTemplate stringRedisTemplate;

    @Override
    public void onMessage(MapRecord<String, String, String> message) {
        try {
            String recordId = message.getId().getValue();
            String dedupKey = DEDUP_KEY_PREFIX + recordId;

            Boolean firstSeen =
                    stringRedisTemplate
                            .opsForValue()
                            .setIfAbsent(dedupKey, "1", DEDUP_TTL);

            if (Boolean.TRUE.equals(firstSeen)) {
                Map<String, String> value = message.getValue();
                String intraId = value.get("intraId");
                String text = value.get("message");

                log.info("📥 [Consumer] Redis Stream에서 슬랙 알림 메시지 수신: {}", intraId);
                slackBotService.sendDm(intraId, text);
            } else {
                log.warn("🔁 [Consumer] 이미 처리된 메시지(redelivery), 중복 전송 스킵: {}", recordId);
            }

            redisTemplate
                    .opsForStream()
                    .acknowledge(RedisStreamConfig.CONSUMER_GROUP_NAME, message);

            redisTemplate.opsForStream().delete(message);

        } catch (Exception e) {
            log.error("🚨 [Consumer] 슬랙 알림 처리 중 에러 발생: {}", e.getMessage());
        }
    }
}
