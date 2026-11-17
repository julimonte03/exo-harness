package com.example.library.members;

import static com.google.common.base.Preconditions.checkArgument;
import static com.google.common.base.Preconditions.checkState;

import com.example.library.loans.LoanRepository;
import com.google.common.base.Strings;
import java.time.LocalDate;
import java.util.Locale;
import java.util.NoSuchElementException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
@RequiredArgsConstructor
public class MemberService {

    private final MemberRepository members;
    private final LoanRepository loans;

    public Member register(String fullName, String email, MemberType type) {
        checkArgument(!Strings.isNullOrEmpty(fullName) && !fullName.isBlank(),
                "Full name is required");
        checkArgument(type != null, "Member type is required");
        String normalized = normalizeEmail(email);
        if (type == MemberType.STUDENT) {
            checkArgument(normalized.endsWith(MemberType.STUDENT_EMAIL_DOMAIN),
                    "Students register with their %s address", MemberType.STUDENT_EMAIL_DOMAIN);
        }
        checkState(!members.existsByEmail(normalized), "%s is already a member", normalized);
        return members.save(new Member(fullName.strip(), normalized, type, LocalDate.now()));
    }

    @Transactional(readOnly = true)
    public Member get(long id) {
        return members.findById(id)
                .orElseThrow(() -> new NoSuchElementException("Member " + id + " not found"));
    }

    /** Closes the membership. Every loan has to be returned first. */
    public Member close(long id) {
        Member member = get(id);
        long active = loans.countByMemberIdAndReturnedOnIsNull(id);
        checkState(active == 0, "Member %s still has %s active loans", id, active);
        member.close();
        return member;
    }

    static String normalizeEmail(String email) {
        checkArgument(!Strings.isNullOrEmpty(email), "Email is required");
        String normalized = email.strip().toLowerCase(Locale.ROOT);
        int at = normalized.indexOf('@');
        checkArgument(at > 0 && at == normalized.lastIndexOf('@')
                && normalized.indexOf('.', at) > at + 1, "Not a valid email address: %s", email);
        return normalized;
    }
}
