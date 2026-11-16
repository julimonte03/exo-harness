package com.example.library.books;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.example.library.common.BusinessRuleException;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

class IsbnTest {

    @ParameterizedTest
    @CsvSource({
            "978-0-306-40615-7, 9780306406157",
            "0-306-40615-2, 9780306406157",
            "080442957X, 9780804429573",
    })
    void normalisesIsbn10AndIsbn13ToThirteenDigits(String raw, String expected) {
        assertThat(Isbn.parse(raw).value()).isEqualTo(expected);
    }

    @ParameterizedTest
    @ValueSource(strings = {"978-0-306-40615-8", "0-306-40615-3", "12345", "978030640615A"})
    void rejectsBadChecksumsAndShapes(String raw) {
        assertThatThrownBy(() -> Isbn.parse(raw))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("Not a valid ISBN");
    }
}
