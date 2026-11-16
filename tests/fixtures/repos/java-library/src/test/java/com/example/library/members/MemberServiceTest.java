package com.example.library.members;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import com.example.library.loans.LoanRepository;
import java.time.LocalDate;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class MemberServiceTest {

    @Mock MemberRepository members;
    @Mock LoanRepository loans;
    @InjectMocks MemberService service;

    private final Member ana = new Member("Ana Reader", "ana.reader@example.com",
            MemberType.PUBLIC, LocalDate.of(2024, 3, 1));

    @Test
    void normalisesTheEmailBeforeCheckingDuplicates() {
        when(members.existsByEmail("ana.reader@example.com")).thenReturn(true);

        assertThatThrownBy(() -> service.register("Ana Reader", " Ana.Reader@Example.COM ",
                MemberType.PUBLIC)).hasMessageContaining("already a member");
    }

    @Test
    void studentsRegisterWithTheirUniversityAddress() {
        assertThatThrownBy(() -> service.register("Leo Student", "leo@example.com",
                MemberType.STUDENT)).hasMessageContaining("students.example.com");
    }

    @Test
    void cannotCloseWhileLoansAreActive() {
        when(members.findById(7L)).thenReturn(Optional.of(ana));
        when(loans.countByMemberIdAndReturnedOnIsNull(7L)).thenReturn(2L, 0L);

        assertThatThrownBy(() -> service.close(7)).hasMessageContaining("2 active loans");
        assertThat(ana.canBorrow()).isTrue();

        service.close(7);
        assertThat(ana.getStatus()).isEqualTo(MemberStatus.CLOSED);
        assertThat(ana.canBorrow()).isFalse();
    }
}
