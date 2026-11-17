package com.example.library.books;

public enum BookStatus {
    /** On the catalog and lendable while copies are on the shelf. */
    ACTIVE,
    /** Kept for loan history only; never lent again. */
    RETIRED
}
