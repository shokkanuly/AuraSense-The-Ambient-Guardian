# Mobile Subsystem Conventions — AuraSense

## Platform
- **Framework**: Flutter (Dart)
- **Targets**: iOS + Android from a single codebase
- **Min SDK**: iOS 16 / Android API 26

## State management
- **Pattern**: Riverpod (providers + notifiers) — do NOT introduce BLoC, Provider, or GetX
- **Global state**: `lib/providers/` directory; one file per domain (e.g. `hub_provider.dart`, `events_provider.dart`)

## Networking
- **LAN-first**: connects to hub via local IP (stored in secure storage after pairing)
- **Fallback**: cloud relay WebSocket if LAN unreachable
- **HTTP client**: Dio with a shared `ApiClient` singleton (`lib/services/api_client.dart`)
- **WebSocket**: `lib/services/event_stream.dart` — reconnects with exponential backoff

## Offline-first
- **Local DB**: Drift (SQLite wrapper for Flutter)
- **Sync strategy**: write-through cache; WebSocket events appended locally; pull-on-reconnect for gaps

## Folder structure
```
lib/
  main.dart
  providers/       # Riverpod providers
  screens/         # one folder per screen
  widgets/         # shared reusable widgets
  services/        # ApiClient, EventStream, OtaService
  models/          # Dart data classes (generated from shared/types via build_runner)
  theme/           # AppTheme, colors, typography
```

## API contract
- Dart models in `lib/models/` are generated from `shared/types/api_types.py` via a codegen script (`scripts/gen_dart_models.py`)
- Never hand-write Dart models that duplicate backend types — always run codegen

## Push notifications
- Firebase Cloud Messaging (FCM) for out-of-LAN alerts
- Hub sends push via thin cloud relay; no raw sensor data ever goes to cloud

## Navigation
- **Router**: go_router; all routes defined in `lib/router.dart`
- **Deep links**: `aurasense://events/{event_id}`
