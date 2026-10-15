# Catholic Background — Android

Shows a work of Catholic sacred art every day, with a daily notification, and
sets it as the wallpaper of the phone only when the user says so. It uses the
server of the `catholic_background_server` project (by default
`https://simba.fdi.ucm.es/background`).

Author: Luis Llana <luis.llana.diaz@gmail.com>
License: GPL-3.0-or-later (see `LICENSE`)

Requirements: Android 8.0 (API 26) or later.

## What it does

- **Daily notification** at the chosen time (9:00 by default) with the reason
  (saint, celebration or liturgical season), title, author and year of the
  artwork of the day and its picture. Tapping it opens the application. On
  Android 13 or later the application asks for permission to show it.
- **Question of the day**: the first time the application is opened each day
  (for example from the notification) it asks what to do with the image of
  today: set it as the wallpaper of the home screen, of the lock screen, of both,
  or only see it. Nothing is preselected and it must be answered. The
  application **never changes the wallpaper by itself**.
- **Main screen**: the image of any day with its data (reason, title, author,
  year, comment, other data, license and source); previous and next day, a
  calendar and Today. **Use as wallpaper…** asks the same question for the day
  shown; **Edit this image** opens the page of the artwork in the content
  manager (editors must log in).
- **The wallpaper**: the artwork complete and as big as possible, the rest of the
  screen filled with a blurred copy of it, its average color or a color. The
  server adds a label with the reason, title, author and year (it can be turned
  off).
- **Settings**: server, language of the texts (by default that of the phone;
  the list comes from the server), label, notification and its time, and how to
  fill the screen.
- Interface in English and Spanish, following the language of the phone.

The notification uses an alarm of the system (`setAndAllowWhileIdle`, no special
permission): it goes off even when the phone is idle, at most a few minutes late,
and it is set again after a reboot, an update or a change of the clock. If the
phone was off at that time, it is shown as soon as possible that day. If the
server cannot be reached then, WorkManager tries again when there is network.
**Settings → Show it now** tests it, and Settings warns when the system has the
notifications of the application turned off. Some manufacturers (Xiaomi, Huawei,
Samsung…) stop the alarms of applications with battery restrictions: in that case,
set the battery use of the application to "Unrestricted".
Version 0.6.0 removed the automatic wallpaper of 0.5.0: updating cancels its
periodic check.

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

2. Tell Gradle where it is, in `~/.gradle/gradle.properties` (your home, never
   in the repository; `chmod 600` it):

       catholicBackground.storeFile=/home/<user>/catholic-background-upload.jks
       catholicBackground.storePassword=<password of the keystore>
       # Only if they are not the default ones:
       # catholicBackground.keyAlias=upload
       # catholicBackground.keyPassword=<password of the key>

   Then the bundle comes out signed (without those properties it is not signed):

       sh gradlew bundleRelease     # app/build/outputs/bundle/release/app-release.aab
       jarsigner -verify app/build/outputs/bundle/release/app-release.aab   # "jar verified."

3. Upload the `.aab` in the Google Play Console (Play App Signing signs the final
   application). Increase `versionCode` in `app/build.gradle.kts` for every new
   upload.

The application id `es.llana.catholicbackground` cannot be changed once the
application is published.
