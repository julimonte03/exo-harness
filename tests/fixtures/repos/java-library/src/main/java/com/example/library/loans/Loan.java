package com.example.library.loans;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDate;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "loans")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Loan {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "book_id", nullable = false)
    private Long bookId;

    @Column(name = "member_id", nullable = false)
    private Long memberId;

    @Column(name = "borrowed_on", nullable = false)
    private LocalDate borrowedOn;

    @Column(name = "due_on", nullable = false)
    private LocalDate dueOn;

    @Column(name = "returned_on")
    private LocalDate returnedOn;

    @Column(nullable = false)
    private int renewals;

    @Column(name = "fine_cents", nullable = false)
    private long fineCents;

    public Loan(Long bookId, Long memberId, LocalDate borrowedOn, LocalDate dueOn) {
        this.bookId = bookId;
        this.memberId = memberId;
        this.borrowedOn = borrowedOn;
        this.dueOn = dueOn;
    }

    public boolean isActive() {
        return returnedOn == null;
    }

    public boolean isOverdue(LocalDate today) {
        return isActive() && today.isAfter(dueOn);
    }

    void renew(LocalDate newDueOn) {
        renewals++;
        dueOn = newDueOn;
    }

    void close(LocalDate returnedOn, long fineCents) {
        this.returnedOn = returnedOn;
        this.fineCents = fineCents;
    }
}
