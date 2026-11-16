package com.example.library.members;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDate;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "members")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Member {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "full_name", nullable = false)
    private String fullName;

    @Column(nullable = false, unique = true)
    private String email;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private MemberType type;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private MemberStatus status = MemberStatus.ACTIVE;

    @Column(name = "joined_on", nullable = false)
    private LocalDate joinedOn;

    public Member(String fullName, String email, MemberType type, LocalDate joinedOn) {
        this.fullName = fullName;
        this.email = email;
        this.type = type;
        this.joinedOn = joinedOn;
    }

    /** Closed memberships keep their loan history but never borrow again. */
    public boolean canBorrow() {
        return status == MemberStatus.ACTIVE;
    }

    void close() {
        status = MemberStatus.CLOSED;
    }
}
