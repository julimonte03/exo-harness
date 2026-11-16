package com.example.library.books;

public enum Genre {
    FICTION,
    NON_FICTION,
    CHILDREN,
    SCIENCE,
    HISTORY,
    POETRY,
    REFERENCE;

    /** Reference works (dictionaries, atlases) are read in the branch and never lent. */
    public boolean isLendable() {
        return this != REFERENCE;
    }
}
