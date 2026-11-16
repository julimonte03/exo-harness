package com.example.library.books;

import com.example.library.common.BusinessRuleException;
import com.example.library.common.NotFoundException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class BookService {

    /** Shelf space per title at a branch; larger orders go to the regional depot. */
    static final int MAX_COPIES_PER_TITLE = 20;

    private final BookRepository books;
    private final com.example.library.notifications.Notifier notifier;
    private final String catalogTeamEmail;

    public BookService(BookRepository books,
                       com.example.library.notifications.Notifier notifier,
                       @Value("${library.catalog.team-email}") String catalogTeamEmail) {
        this.books = books;
        this.notifier = notifier;
        this.catalogTeamEmail = catalogTeamEmail;
    }

    public Book register(BookRequest request) {
        Isbn isbn = Isbn.parse(request.isbn());
        if (books.existsByIsbn(isbn.value())) {
            throw new BusinessRuleException("duplicate_isbn",
                    "ISBN " + isbn.value() + " is already in the catalog");
        }
        int copies = request.copies() == null ? 1 : request.copies();
        if (copies < 1 || copies > MAX_COPIES_PER_TITLE) {
            throw new BusinessRuleException("copies_out_of_range",
                    "A title holds between 1 and " + MAX_COPIES_PER_TITLE + " copies");
        }
        Genre genre = request.genre() == null ? Genre.FICTION : request.genre();
        return books.save(new Book(isbn, requireText(request.title(), "title"),
                requireText(request.author(), "author"), genre, copies));
    }

    @Transactional(readOnly = true)
    public Book get(long id) {
        return books.findById(id).orElseThrow(() -> new NotFoundException("Book", id));
    }

    /** Retired titles never show up in the public catalog. */
    @Transactional(readOnly = true)
    public Page<Book> search(BookSearch search) {
        return books.search(search.text(), search.genre(), BookStatus.ACTIVE, search.pageable());
    }

    public Book addCopies(long id, int count) {
        Book book = get(id);
        if (book.getStatus() == BookStatus.RETIRED) {
            throw new BusinessRuleException("book_retired", "Retired titles take no new copies");
        }
        if (book.getTotalCopies() + count > MAX_COPIES_PER_TITLE) {
            throw new BusinessRuleException("copies_out_of_range",
                    "A title holds at most " + MAX_COPIES_PER_TITLE + " copies");
        }
        book.addCopies(count);
        return book;
    }

    public Book retire(long id) {
        Book book = get(id);
        book.retire();
        notifier.send(catalogTeamEmail, "Title retired: " + book.getTitle(),
                "ISBN " + book.getIsbn() + " is out of circulation. Remove it from the shelves.");
        return book;
    }

    private static String requireText(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(field + " is required");
        }
        return value.strip();
    }
}
