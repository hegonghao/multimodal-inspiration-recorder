/// Main entry point for the multimodal inspiration recorder app
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'core/constants.dart';
import 'core/routes.dart';
import 'core/themes.dart';
import 'data/database.dart';
import 'data/repositories/inspiration_repository.dart';
import 'data/services/api_service.dart';
import 'data/services/audio_service.dart';
import 'data/services/camera_service.dart';
import 'data/services/notification_service.dart';
import 'data/services/storage_service.dart';
import 'data/services/sync/connectivity_service.dart';
import 'data/services/sync/sync_service.dart';
import 'presentation/providers/inspiration_provider.dart';

void main() async {
  // Ensure Flutter binding is initialized
  WidgetsFlutterBinding.ensureInitialized();

  // Set preferred device orientations (portrait only for mobile)
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Initialize services
  final database = AppDatabase();
  final storageService = await StorageService.getInstance();

  final apiService = ApiService(
    baseUrl: storageService.getString(StorageService.keyApiBaseUrl) ?? ApiConstants.defaultBaseUrl,
  );
  final audioService = AudioService();
  final cameraService = CameraService();

  // Initialize notification service
  final notificationService = NotificationService();
  await notificationService.initialize();

  // Initialize connectivity and sync services
  final connectivityService = ConnectivityService();
  final inspirationRepository = InspirationRepository(database);
  final syncService = SyncService(
    repository: inspirationRepository,
    apiService: apiService,
    connectivityService: connectivityService,
    database: database,
    notificationService: notificationService,
  );

  // Run the app
  runApp(
    MultiProvider(
      providers: [
        // Provide database instance
        Provider<AppDatabase>.value(value: database),

        // Provide repository
        Provider<InspirationRepository>.value(value: inspirationRepository),

        // Provide services
        Provider<ApiService>.value(value: apiService),
        Provider<AudioService>.value(value: audioService),
        Provider<CameraService>.value(value: cameraService),
        Provider<StorageService>.value(value: storageService),
        Provider<NotificationService>.value(value: notificationService),

        // Provide connectivity and sync services
        ChangeNotifierProvider<ConnectivityService>.value(
          value: connectivityService,
        ),
        ChangeNotifierProvider<SyncService>.value(
          value: syncService,
        ),

        // Provide state management
        ChangeNotifierProvider(
          create: (context) => InspirationProvider(
            apiService: apiService,
            audioService: audioService,
            cameraService: cameraService,
            storageService: storageService,
            database: database,
          ),
        ),
      ],
      child: const MyApp(),
    ),
  );
}

/// Root application widget
class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      // App metadata
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,

      // Theme configuration
      theme: AppThemes.lightTheme,
      darkTheme: AppThemes.darkTheme,
      themeMode: ThemeMode.system, // Follow system theme

      // Routing configuration
      initialRoute: Routes.home,
      onGenerateRoute: AppRouter.generateRoute,

      // Builder for additional configuration
      builder: (context, child) {
        return MediaQuery(
          // Prevent text scaling based on system settings
          data: MediaQuery.of(context).copyWith(
            textScaler: TextScaler.noScaling,
          ),
          child: child!,
        );
      },
    );
  }
}
