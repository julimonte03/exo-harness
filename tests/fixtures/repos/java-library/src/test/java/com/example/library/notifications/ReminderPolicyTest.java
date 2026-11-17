package com.example.library.notifications;

import static org.assertj.core.api.Assertions.assertThat;

import com.example.library.common.Dates;
import com.example.library.notifications.ReminderPolicy.Reminder;
import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Optional;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class ReminderPolicyTest {

    private static final LocalDate TODAY = LocalDate.of(2025, 3, 10);
    private final ReminderPolicy policy = new ReminderPolicy();

    @BeforeEach
    void pinTheClock() {
        Dates.useClock(Clock.fixed(TODAY.atStartOfDay(ZoneOffset.UTC).toInstant(), ZoneOffset.UTC));
    }

    @AfterEach
    void resetClock() {
        Dates.resetClock();
    }

    @ParameterizedTest(name = "due in {0} days -> {1}")
    @CsvSource({"3,", "2, DUE_SOON", "1,", "0,", "-1, OVERDUE", "-2,", "-7, OVERDUE",
            "-14, OVERDUE", "-15,", "-30,"})
    void sendsOneNoticePerMilestone(int dueInDays, Reminder expected) {
        assertThat(policy.reminderFor(TODAY.plusDays(dueInDays)))
                .isEqualTo(Optional.ofNullable(expected));
    }
}
