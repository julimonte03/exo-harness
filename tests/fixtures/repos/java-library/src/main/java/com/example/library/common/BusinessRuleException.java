package com.example.library.common;

import lombok.Getter;

/** A well-formed request that breaks a circulation rule. The code is stable for API clients. */
@Getter
public class BusinessRuleException extends RuntimeException {

    private final String code;

    public BusinessRuleException(String code, String message) {
        super(message);
        this.code = code;
    }
}
