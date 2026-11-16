package com.example.library.notifications;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/** Logs notices (never the address) until the branch mail relay is provisioned. */
@Slf4j
@Component
public class LogNotifier implements Notifier {

    @Override
    public void send(String to, String subject, String body) {
        log.info("notice queued subject='{}'", subject);
    }
}
