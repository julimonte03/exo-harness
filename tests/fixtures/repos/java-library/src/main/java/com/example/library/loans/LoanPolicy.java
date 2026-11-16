package com.example.library.loans;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** Branch-wide circulation settings, bound from {@code library.loans} in application.yml. */
@ConfigurationProperties(prefix = "library.loans")
public record LoanPolicy(int maxRenewals, long dailyFineCents, long maxFineCents, int graceDays) {}
