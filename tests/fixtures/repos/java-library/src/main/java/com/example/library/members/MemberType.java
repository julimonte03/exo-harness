package com.example.library.members;

/** Membership tiers and the circulation limits that come with each one. */
public enum MemberType {
    STUDENT(3, 14),
    PUBLIC(5, 21),
    STAFF(10, 28);

    /** Student cards are issued against the university directory only. */
    public static final String STUDENT_EMAIL_DOMAIN = "@students.example.com";

    private final int maxActiveLoans;
    private final int loanDays;

    MemberType(int maxActiveLoans, int loanDays) {
        this.maxActiveLoans = maxActiveLoans;
        this.loanDays = loanDays;
    }

    public int maxActiveLoans() {
        return maxActiveLoans;
    }

    public int loanDays() {
        return loanDays;
    }
}
