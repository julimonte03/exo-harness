package com.example.library.loans;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.LocalDate;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class FineCalculatorTest {

    private final FineCalculator calculator = new FineCalculator(new LoanPolicy(2, 25, 1000, 1));
    private final LocalDate due = LocalDate.of(2025, 3, 10);

    @ParameterizedTest(name = "{0} days late -> {1} cents")
    @CsvSource({"-3, 0", "0, 0", "1, 0", "2, 50", "10, 250", "40, 1000", "365, 1000"})
    void chargesEveryDayLateOnceTheGraceDayIsOverUpToTheCap(long daysLate, long cents) {
        assertThat(calculator.fineCents(due, due.plusDays(daysLate))).isEqualTo(cents);
    }
}
