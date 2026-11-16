package com.example.library.loans;

import java.time.LocalDate;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LoanRepository extends JpaRepository<Loan, Long> {

    long countByMemberIdAndReturnedOnIsNull(Long memberId);

    List<Loan> findByReturnedOnIsNullAndDueOnBetween(LocalDate from, LocalDate to);
}
