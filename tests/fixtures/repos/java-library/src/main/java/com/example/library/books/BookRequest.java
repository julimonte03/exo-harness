package com.example.library.books;

/** Body of POST /api/books. Copies default to one. */
public record BookRequest(String isbn, String title, String author, Genre genre, Integer copies) {
}
