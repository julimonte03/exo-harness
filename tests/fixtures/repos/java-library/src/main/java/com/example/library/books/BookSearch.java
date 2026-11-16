package com.example.library.books;

import com.example.library.common.BusinessRuleException;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;

/** Validated catalog search parameters. */
public record BookSearch(String text, Genre genre, int page, int size) {

    public static final int DEFAULT_PAGE_SIZE = 20;
    public static final int MAX_PAGE_SIZE = 50;
    public static final int MIN_QUERY_LENGTH = 2;

    public static BookSearch of(String text, Genre genre, Integer page, Integer size) {
        String query = text == null ? "" : text.strip();
        if (!query.isEmpty() && query.length() < MIN_QUERY_LENGTH) {
            throw new BusinessRuleException("query_too_short",
                    "Search text needs at least " + MIN_QUERY_LENGTH + " characters");
        }
        int pageNumber = page == null ? 0 : page;
        if (pageNumber < 0) {
            throw new IllegalArgumentException("Page numbers start at 0");
        }
        int pageSize = size == null ? DEFAULT_PAGE_SIZE : size;
        if (pageSize < 1) {
            throw new IllegalArgumentException("Page size must be positive");
        }
        return new BookSearch(query, genre, pageNumber, Math.min(pageSize, MAX_PAGE_SIZE));
    }

    public Pageable pageable() {
        return PageRequest.of(page, size, Sort.by("title").ascending().and(Sort.by("id")));
    }
}
