package com.example.library.loans;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/loans")
@RequiredArgsConstructor
public class LoanController {

    public record Checkout(long memberId, long bookId) {}

    private final LoanService service;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Loan checkout(@RequestBody Checkout body) {
        return service.checkout(body.memberId(), body.bookId());
    }

    @PostMapping("/{id}/renewal")
    public Loan renew(@PathVariable long id) {
        return service.renew(id);
    }

    @PostMapping("/{id}/return")
    public Loan returnLoan(@PathVariable long id) {
        return service.returnLoan(id);
    }
}
