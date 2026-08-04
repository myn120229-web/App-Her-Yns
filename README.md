# App-Her-Yns - Unemployed Android App

## Overview
Modern Android application built with Kotlin and Jetpack Compose.
Designed with Clean Architecture and full customization capabilities.

## Features
- **Job Listing** - Browse available opportunities
- **Admin Dashboard** - Full management panel for the owner
- **Custom API Endpoint** - Users can configure their own API URL and Key
- **Remote Configuration** - UI theme and behavior can be updated remotely
- **User Management** - Owner can restrict/unrestrict users
- **Master Key System** - Secure admin access

## Tech Stack
- Kotlin + Jetpack Compose
- MVVM + Clean Architecture
- Retrofit for networking
- StateFlow for state management

## Files
- `app-universal-release.apk` - Universal APK (ready to install)
- `unemployed_android_project.tar.gz` - Source code archive
- Source files in root directory

## Master Key
See `app/src/main/java/com/unemployed/app/SecurityConfig.kt`

## Build
```bash
./gradlew assembleUniversalRelease
```

---
Built with ❤️ by Hermes Agent
