# Catholic Background — Android

Sets a work of Catholic sacred art as the wallpaper of the phone every day, and
shows a daily notification with it. It uses the server of the
`catholic_background_server` project (by default
`https://simba.fdi.ucm.es/background`).

Author: Luis Llana <luis.llana.diaz@gmail.com>
License: GPL-3.0-or-later (see `LICENSE`)

Requirements: Android 8.0 (API 26) or later.

## What it does

- **Daily notification** at the chosen time (9:00 by default) with the reason
  (saint, celebration or liturgical season), title, author and year of the
  artwork of the day and its picture. Tapping it opens the application. On
  Android 13 or later the application asks for permission to show it.
- **Main screen**: the image of any day with its data (reason, title, author,
  year, comment, other data, license and source); previous and next day, a
  calendar and Today. **Use as wallpaper** (the day shown becomes the wallpaper
  until the next automatic check, which returns to today), **Edit this image**
  (opens the page of the artwork in the content manager; editors must log in)
  and **Refresh wallpaper**.
- **Automatic wallpaper** (optional): every hour by default it checks the server
  and changes the wallpaper of the home screen, the lock screen or both when the
  image changes. The artwork is shown complete and as big as possible, and the
  rest of the screen is filled with a blurred copy of it, its average color or a
  color. The server adds a label with the reason, title, author and year (it can
  be turned off).
- **Settings**: server, language of the texts (by default that of the phone;
  the list comes from the server), label, notification and its time, automatic
  wallpaper, where, how to fill the screen and how often to check.
- Interface in English and Spanish, following the language of the phone.

The periodic work uses WorkManager: it survives reboots and respects the battery
savings of Android, so checks and the notification may be a few minutes late
when the phone is idle. Checks are not done more often than every 15 minutes
(minimum of Android).

## Build

Needs a JDK 17 or later and the Android SDK (platform 37):

    sudo apt install openjdk-21-jdk-headless
    # Android SDK: install Android Studio, or the command line tools from
    # https://developer.android.com/studio#command-line-tools-only, then:
    sdkmanager "platforms;android-37.0" "build-tools;37.0.0"
    echo "sdk.dir=$HOME/Android/Sdk" > local.properties     # where the SDK is

    sh gradlew assembleDebug        # app/build/outputs/apk/debug/app-debug.apk
    sh gradlew testDebugUnitTest    # unit tests
    sh gradlew lintDebug            # Android Lint

The project can also be opened with Android Studio.

## Install on a phone for testing

Copy `app-debug.apk` to the phone and open it (allow installing apps from that
source when Android asks), or with the phone connected by USB and USB debugging
enabled:

    adb install -r app/build/outputs/apk/debug/app-debug.apk

## Publish on Google Play

1. Create an upload key once (keep it and its passwords safe: it is needed for
   every update):

       keytool -genkeypair -v -keystore ~/catholic-background-upload.jks \
           -alias upload -keyalg RSA -keysize 4096 -validity 10000

2. Build the Android App Bundle signed with it (for example with Android Studio:
   Build → Generate Signed App Bundle, or configuring `signingConfigs` in
   `app/build.gradle.kts` with the passwords kept out of the repository):

       sh gradlew bundleRelease     # app/build/outputs/bundle/release/app-release.aab

3. Upload the `.aab` in the Google Play Console (Play App Signing signs the final
   application). Increase `versionCode` in `app/build.gradle.kts` for every new
   upload.

The application id `es.llana.catholicbackground` cannot be changed once the
application is published.
