package com.example.library.loans;

import com.example.library.common.Dates;
import java.time.LocalDate;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class FineCalculator {

    private final LoanPolicy policy;

    /** Returns inside the grace period are free; after it every day late counts, up to the cap. */
    public long fineCents(LocalDate dueOn, LocalDate returnedOn) {
        long daysLate = Dates.daysBetween(dueOn, returnedOn);
        if (daysLate <= policy.graceDays()) {
            return 0;
        }
        return Math.min(daysLate * policy.dailyFineCents(), policy.maxFineCents());
    }
}
