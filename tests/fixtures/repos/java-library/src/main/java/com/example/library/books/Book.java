package com.example.library.books;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * A catalog title and the stock of physical copies the branch owns.
 *
 * <p>Copies leave and come back through {@link com.example.library.loans.LoanService}; the two
 * counters here are the only source of truth for availability.
 */
@Entity
@Table(name = "books")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Book {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 13)
    private String isbn;

    @Column(nullable = false)
    private String title;

    @Column(nullable = false)
    private String author;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private Genre genre;

    @Column(name = "total_copies", nullable = false)
    private int totalCopies;

    @Column(name = "available_copies", nullable = false)
    private int availableCopies;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private BookStatus status = BookStatus.ACTIVE;

    public Book(Isbn isbn, String title, String author, Genre genre, int copies) {
        if (copies < 1) {
            throw new IllegalArgumentException("A new title needs at least one copy");
        }
        this.isbn = isbn.value();
        this.title = title;
        this.author = author;
        this.genre = genre;
        this.totalCopies = copies;
        this.availableCopies = copies;
    }

    /** True when a member could walk out with a copy right now. */
    public boolean isLendable() {
        return status == BookStatus.ACTIVE && genre.isLendable() && availableCopies > 0;
    }

    public int copiesOnLoan() {
        return totalCopies - availableCopies;
    }

    public void checkOutCopy() {
        if (status == BookStatus.RETIRED) {
            throw new IllegalStateException("Book " + isbn + " has been retired");
        }
        if (!genre.isLendable()) {
            throw new IllegalStateException("Reference works stay in the reading room");
        }
        if (availableCopies == 0) {
            throw new IllegalStateException("No copies of " + isbn + " are on the shelf");
        }
        availableCopies--;
    }

    public void returnCopy() {
        if (availableCopies >= totalCopies) {
            throw new IllegalStateException("Every copy of " + isbn + " is already on the shelf");
        }
        availableCopies++;
    }

    public void addCopies(int count) {
        if (count < 1) {
            throw new IllegalArgumentException("Copies to add must be positive");
        }
        totalCopies += count;
        availableCopies += count;
    }

    /** Takes the title out of circulation; no copy may be out on loan. */
    public void retire() {
        if (copiesOnLoan() > 0) {
            throw new IllegalStateException(
                    copiesOnLoan() + " copies of " + isbn + " are still on loan");
        }
        status = BookStatus.RETIRED;
    }
}
