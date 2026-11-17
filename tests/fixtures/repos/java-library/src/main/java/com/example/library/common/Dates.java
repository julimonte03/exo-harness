package com.example.library.common;

import java.time.Clock;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;

/** Circulation rules count whole days on the branch calendar; tests pin the clock. */
public final class Dates {

    private static Clock clock = Clock.systemDefaultZone();

    private Dates() {
    }

    public static LocalDate today() {
        return LocalDate.now(clock);
    }

    public static long daysBetween(LocalDate from, LocalDate to) {
        return ChronoUnit.DAYS.between(from, to);
    }

    public static void useClock(Clock fixed) {
        clock = fixed;
    }

    public static void resetClock() {
        clock = Clock.systemDefaultZone();
    }
}
