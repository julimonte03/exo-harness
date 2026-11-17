package com.example.library.books;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface BookRepository extends JpaRepository<Book, Long> {

    boolean existsByIsbn(String isbn);

    @Query("""
            select b from Book b
            where b.status = :status
              and (:genre is null or b.genre = :genre)
              and (lower(b.title) like lower(concat('%', :text, '%'))
                   or lower(b.author) like lower(concat('%', :text, '%')))
            """)
    Page<Book> search(@Param("text") String text, @Param("genre") Genre genre,
                      @Param("status") BookStatus status, Pageable pageable);
}
