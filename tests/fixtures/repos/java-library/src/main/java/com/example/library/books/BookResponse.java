package com.example.library.books;

public record BookResponse(Long id, String isbn, String title, String author, Genre genre,
                           int totalCopies, int availableCopies, BookStatus status,
                           boolean lendable) {

    public static BookResponse from(Book b) {
        return new BookResponse(b.getId(), b.getIsbn(), b.getTitle(), b.getAuthor(), b.getGenre(),
                b.getTotalCopies(), b.getAvailableCopies(), b.getStatus(), b.isLendable());
    }
}
