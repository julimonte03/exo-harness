package com.example.library.notifications;

import static com.example.library.common.Dates.today;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.Optional;
import java.util.Set;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

/** Decides which loans get a notice today: one per milestone, never a daily nag. */
@Component
public class ReminderPolicy {

    @RequiredArgsConstructor
    public enum Reminder {
        DUE_SOON("Due soon: "),
        OVERDUE("Overdue: ");

        private final String prefix;

        public String subject(String title) {
            return prefix + title;
        }
    }

    public static final int DAYS_BEFORE_DUE = 2;
    public static final int LAST_OVERDUE_NOTICE_DAY = 14;
    static final Set<Long> OVERDUE_NOTICE_DAYS = Set.of(1L, 7L, (long) LAST_OVERDUE_NOTICE_DAY);

    public Optional<Reminder> reminderFor(LocalDate dueOn) {
        long daysLate = ChronoUnit.DAYS.between(dueOn, today());
        if (daysLate == -DAYS_BEFORE_DUE) {
            return Optional.of(Reminder.DUE_SOON);
        }
        if (OVERDUE_NOTICE_DAYS.contains(daysLate)) {
            return Optional.of(Reminder.OVERDUE);
        }
        return Optional.empty();
    }
}
