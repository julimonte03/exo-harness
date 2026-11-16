package com.example.library.members;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/members")
@RequiredArgsConstructor
public class MemberController {

    public record Registration(String fullName, String email, MemberType type) {}

    private final MemberService service;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Member register(@RequestBody Registration body) {
        return service.register(body.fullName(), body.email(), body.type());
    }

    @GetMapping("/{id}")
    public Member get(@PathVariable long id) {
        return service.get(id);
    }

    @DeleteMapping("/{id}")
    public Member close(@PathVariable long id) {
        return service.close(id);
    }
}
