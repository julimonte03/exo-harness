package com.example.library.common;

import java.util.NoSuchElementException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/** Maps domain failures to the error body documented in openapi.yaml. */
@RestControllerAdvice
public class ApiErrorHandler {

    public record ApiError(String code, String message) {}

    @ExceptionHandler({NotFoundException.class, NoSuchElementException.class})
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ApiError notFound(RuntimeException ex) {
        return new ApiError("not_found", ex.getMessage());
    }

    @ExceptionHandler(BusinessRuleException.class)
    @ResponseStatus(HttpStatus.UNPROCESSABLE_ENTITY)
    public ApiError ruleBroken(BusinessRuleException ex) {
        return new ApiError(ex.getCode(), ex.getMessage());
    }

    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ApiError invalid(IllegalArgumentException ex) {
        return new ApiError("invalid_request", ex.getMessage());
    }

    @ExceptionHandler(IllegalStateException.class)
    @ResponseStatus(HttpStatus.CONFLICT)
    public ApiError conflict(IllegalStateException ex) {
        return new ApiError("conflict", ex.getMessage());
    }
}
