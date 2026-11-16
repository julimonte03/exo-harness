package com.example.library.loans;

import com.example.library.books.*;
import com.example.library.common.BusinessRuleException;
import com.example.library.common.Dates;
import com.example.library.common.NotFoundException;
import com.example.library.members.Member;
import com.example.library.members.MemberRepository;
import com.example.library.members.MemberType;
import com.example.library.notifications.Notifier;
import com.example.library.notifications.ReminderPolicy;
import java.time.LocalDate;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
@RequiredArgsConstructor
public class LoanService {

    private final LoanRepository loans;
    private final BookRepository books;
    private final MemberRepository members;
    private final FineCalculator fines;
    private final LoanPolicy policy;
    private final ReminderPolicy reminders;
    private final Notifier notifier;

    public Loan checkout(long memberId, long bookId) {
        Member member = member(memberId);
        if (!member.canBorrow()) {
            throw new BusinessRuleException("member_not_active",
                    "Member " + memberId + " is " + member.getStatus());
        }
        MemberType type = member.getType();
        if (loans.countByMemberIdAndReturnedOnIsNull(memberId) >= type.maxActiveLoans()) {
            throw new BusinessRuleException("loan_limit_reached",
                    type + " members can have " + type.maxActiveLoans() + " active loans");
        }
        Book book = book(bookId);
        if (!book.getGenre().isLendable()) {
            throw new BusinessRuleException("reference_only",
                    "Reference works are read in the branch");
        }
        book.checkOutCopy();
        LocalDate today = Dates.today();
        return loans.save(new Loan(bookId, memberId, today, today.plusDays(type.loanDays())));
    }

    /** Extends the loan by another full period, counted from the current due date. */
    public Loan renew(long loanId) {
        Loan loan = activeLoan(loanId);
        if (loan.isOverdue(Dates.today())) {
            throw new BusinessRuleException("loan_overdue",
                    "Overdue loans cannot be renewed; return the item instead");
        }
        if (loan.getRenewals() >= policy.maxRenewals()) {
            throw new BusinessRuleException("renewal_limit_reached",
                    "A loan can be renewed at most " + policy.maxRenewals() + " times");
        }
        MemberType type = member(loan.getMemberId()).getType();
        loan.renew(loan.getDueOn().plusDays(type.loanDays()));
        return loan;
    }

    public Loan returnLoan(long loanId) {
        Loan loan = activeLoan(loanId);
        LocalDate today = Dates.today();
        loan.close(today, fines.fineCents(loan.getDueOn(), today));
        book(loan.getBookId()).returnCopy();
        return loan;
    }

    /** Daily sweep that sends the due-soon and overdue notices the reminder policy asks for. */
    @Scheduled(cron = "${library.reminders.cron}")
    @Transactional(readOnly = true)
    public void sendReminders() {
        LocalDate today = Dates.today();
        List<Loan> candidates = loans.findByReturnedOnIsNullAndDueOnBetween(
                today.minusDays(ReminderPolicy.LAST_OVERDUE_NOTICE_DAY),
                today.plusDays(ReminderPolicy.DAYS_BEFORE_DUE));
        for (Loan loan : candidates) {
            reminders.reminderFor(loan.getDueOn()).ifPresent(reminder -> notifier.send(
                    member(loan.getMemberId()).getEmail(),
                    reminder.subject(book(loan.getBookId()).getTitle()),
                    "Due on " + loan.getDueOn() + ". Renew online or return it at the desk."));
        }
    }

    private Loan activeLoan(long id) {
        Loan loan = loans.findById(id).orElseThrow(() -> new NotFoundException("Loan", id));
        if (!loan.isActive()) {
            throw new BusinessRuleException("loan_closed", "Loan " + id + " was already returned");
        }
        return loan;
    }

    private Member member(long id) {
        return members.findById(id).orElseThrow(() -> new NotFoundException("Member", id));
    }

    private Book book(long id) {
        return books.findById(id).orElseThrow(() -> new NotFoundException("Book", id));
    }
}
