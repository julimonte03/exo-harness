package com.example.library.books;

import com.example.library.common.BusinessRuleException;

/**
 * An ISBN normalised to its 13-digit form.
 *
 * <p>Older books print a 10-digit ISBN; it is accepted and converted with the 978 prefix so the
 * catalog never holds the same title twice under two numbers.
 */
public record Isbn(String value) {

    public Isbn {
        if (value == null || value.length() != 13 || !allDigits(value)) {
            throw new IllegalArgumentException("A normalised ISBN has 13 digits: " + value);
        }
    }

    /** Parses user input such as {@code 978-0-306-40615-7} or {@code 0-306-40615-2}. */
    public static Isbn parse(String raw) {
        if (raw == null || raw.isBlank()) {
            throw invalid(raw);
        }
        String compact = raw.strip().replace("-", "").replace(" ", "").toUpperCase();
        if (compact.length() == 10 && isValidIsbn10(compact)) {
            return new Isbn(toIsbn13(compact));
        }
        if (compact.length() == 13 && isValidIsbn13(compact)) {
            return new Isbn(compact);
        }
        throw invalid(raw);
    }

    /** ISBN-10: weights 10..1, the last character may be X (ten), sum divisible by 11. */
    static boolean isValidIsbn10(String digits) {
        int sum = 0;
        for (int i = 0; i < 10; i++) {
            char c = digits.charAt(i);
            boolean ten = i == 9 && c == 'X';
            if (!ten && !Character.isDigit(c)) {
                return false;
            }
            sum += (ten ? 10 : c - '0') * (10 - i);
        }
        return sum % 11 == 0;
    }

    /** ISBN-13 (EAN-13 with a 978 or 979 prefix): weights 1 and 3, sum divisible by 10. */
    static boolean isValidIsbn13(String digits) {
        if (!allDigits(digits) || !(digits.startsWith("978") || digits.startsWith("979"))) {
            return false;
        }
        return weightedSum(digits, 13) % 10 == 0;
    }

    static String toIsbn13(String isbn10) {
        String body = "978" + isbn10.substring(0, 9);
        int check = (10 - weightedSum(body, 12) % 10) % 10;
        return body + check;
    }

    private static int weightedSum(String digits, int length) {
        int sum = 0;
        for (int i = 0; i < length; i++) {
            int digit = digits.charAt(i) - '0';
            sum += (i % 2 == 0) ? digit : digit * 3;
        }
        return sum;
    }

    private static boolean allDigits(String text) {
        return !text.isEmpty() && text.chars().allMatch(Character::isDigit);
    }

    private static BusinessRuleException invalid(String raw) {
        return new BusinessRuleException("invalid_isbn", "Not a valid ISBN-10 or ISBN-13: " + raw);
    }
}
