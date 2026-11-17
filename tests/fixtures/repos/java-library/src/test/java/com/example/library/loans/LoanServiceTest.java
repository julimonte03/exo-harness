package com.example.library.loans;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

import com.example.library.books.Book;
import com.example.library.books.BookRepository;
import com.example.library.books.Genre;
import com.example.library.books.Isbn;
import com.example.library.common.Dates;
import com.example.library.members.Member;
import com.example.library.members.MemberRepository;
import com.example.library.members.MemberType;
import com.example.library.notifications.Notifier;
import com.example.library.notifications.ReminderPolicy;
import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Optional;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class LoanServiceTest {

    static final LocalDate TODAY = LocalDate.of(2025, 3, 10);
    static final LoanPolicy POLICY = new LoanPolicy(2, 25, 1000, 1);

    @Mock LoanRepository loans;
    @Mock BookRepository books;
    @Mock MemberRepository members;
    @Mock Notifier notifier;
    LoanService service;

    private final Book signals =
            new Book(Isbn.parse("9780306406157"), "Signals", "A. Writer", Genre.SCIENCE, 2);

    @BeforeEach
    void setUp() {
        Dates.useClock(Clock.fixed(TODAY.atStartOfDay(ZoneOffset.UTC).toInstant(), ZoneOffset.UTC));
        service = new LoanService(loans, books, members, new FineCalculator(POLICY), POLICY,
                new ReminderPolicy(), notifier);
        Member student = new Member("Leo Student", "leo@students.example.com",
                MemberType.STUDENT, TODAY.minusYears(1));
        lenient().when(members.findById(1L)).thenReturn(Optional.of(student));
    }

    @AfterEach
    void resetClock() {
        Dates.resetClock();
    }

    @Test
    void studentsHoldThreeLoansForFourteenDaysEach() {
        when(books.findById(5L)).thenReturn(Optional.of(signals));
        when(loans.save(any(Loan.class))).thenAnswer(call -> call.getArgument(0));
        when(loans.countByMemberIdAndReturnedOnIsNull(1L)).thenReturn(2L, 3L);

        assertThat(service.checkout(1, 5).getDueOn()).isEqualTo(TODAY.plusDays(14));
        assertThatThrownBy(() -> service.checkout(1, 5)).hasMessageContaining("3 active loans");
    }

    @Test
    void renewalsStopAtThePolicyLimitAndNeverApplyToOverdueLoans() {
        Loan loan = new Loan(5L, 1L, TODAY.minusDays(3), TODAY.plusDays(11));
        Loan late = new Loan(5L, 1L, TODAY.minusDays(20), TODAY.minusDays(6));
        when(loans.findById(9L)).thenReturn(Optional.of(loan));
        when(loans.findById(10L)).thenReturn(Optional.of(late));

        service.renew(9);
        service.renew(9);

        assertThat(loan.getDueOn()).isEqualTo(TODAY.plusDays(11 + 2 * 14));
        assertThatThrownBy(() -> service.renew(9)).hasMessageContaining("at most 2 times");
        assertThatThrownBy(() -> service.renew(10)).hasMessageContaining("cannot be renewed");
    }

    @Test
    void aLateReturnRecordsTheFineAndShelvesTheCopy() {
        Loan loan = new Loan(5L, 1L, TODAY.minusDays(18), TODAY.minusDays(4));
        signals.checkOutCopy();
        when(loans.findById(9L)).thenReturn(Optional.of(loan));
        when(books.findById(5L)).thenReturn(Optional.of(signals));

        service.returnLoan(9);

        assertThat(loan.getFineCents()).isEqualTo(4 * 25);
        assertThat(signals.getAvailableCopies()).isEqualTo(2);
    }
}
