package com.example.library.notifications;

/** Outbound messages to members and staff. */
public interface Notifier {

    void send(String to, String subject, String body);
}
