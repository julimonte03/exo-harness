package com.example.library.books;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/books")
@RequiredArgsConstructor
public class BookController {

    public record CopiesChange(int count) {}

    private final BookService service;

    @GetMapping
    public Page<BookResponse> search(@RequestParam(required = false) String q,
                                     @RequestParam(required = false) Genre genre,
                                     @RequestParam(required = false) Integer page,
                                     @RequestParam(required = false) Integer size) {
        return service.search(BookSearch.of(q, genre, page, size)).map(BookResponse::from);
    }

    @GetMapping("/{id}")
    public BookResponse get(@PathVariable long id) {
        return BookResponse.from(service.get(id));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public BookResponse register(@RequestBody BookRequest request) {
        return BookResponse.from(service.register(request));
    }

    @PostMapping("/{id}/copies")
    public BookResponse addCopies(@PathVariable long id, @RequestBody CopiesChange change) {
        return BookResponse.from(service.addCopies(id, change.count()));
    }

    @DeleteMapping("/{id}")
    public BookResponse retire(@PathVariable long id) {
        return BookResponse.from(service.retire(id));
    }
}
