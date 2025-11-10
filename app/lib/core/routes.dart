/// App navigation routes
library;

import 'package:flutter/material.dart';

import '../presentation/pages/home_page.dart';
import '../presentation/pages/image_input_page.dart';
import '../presentation/pages/settings_page.dart';
import '../presentation/pages/text_input_page.dart';
import '../presentation/pages/voice_input_page.dart';

/// Route names
class Routes {
  Routes._();

  static const String home = '/';
  static const String voiceInput = '/voice';
  static const String imageInput = '/image';
  static const String textInput = '/text'; // Future implementation
  static const String recordsList = '/records'; // Future implementation
  static const String recordDetail = '/record-detail'; // Future implementation
  static const String settings = '/settings'; // Future implementation
  static const String notionSync = '/notion-sync'; // Future implementation
}

/// App router configuration
class AppRouter {
  AppRouter._();

  /// Generate routes based on route settings
  static Route<dynamic> generateRoute(RouteSettings settings) {
    switch (settings.name) {
      case Routes.home:
        return MaterialPageRoute(
          builder: (_) => const HomePage(),
          settings: settings,
        );

      case Routes.voiceInput:
        return MaterialPageRoute(
          builder: (_) => const VoiceInputPage(),
          settings: settings,
        );

      case Routes.imageInput:
        return MaterialPageRoute(
          builder: (_) => const ImageInputPage(),
          settings: settings,
        );

      case Routes.textInput:
        return MaterialPageRoute(
          builder: (_) => const TextInputPage(),
          settings: settings,
        );

      case Routes.recordsList:
        // TODO: Implement RecordsListPage
        return _buildPlaceholderRoute(
          settings: settings,
          title: '历史记录',
          message: '历史记录功能即将推出',
        );

      case Routes.recordDetail:
        // TODO: Implement RecordDetailPage
        return _buildPlaceholderRoute(
          settings: settings,
          title: '记录详情',
          message: '记录详情功能即将推出',
        );

      case Routes.settings:
        return MaterialPageRoute(
          builder: (_) => const SettingsPage(),
          settings: settings,
        );

      case Routes.notionSync:
        // TODO: Implement NotionSyncPage (User Story 4)
        return _buildPlaceholderRoute(
          settings: settings,
          title: 'Notion同步',
          message: 'Notion同步配置功能即将推出',
        );

      default:
        return _buildNotFoundRoute(settings);
    }
  }

  /// Build a placeholder route for unimplemented features
  static MaterialPageRoute _buildPlaceholderRoute({
    required RouteSettings settings,
    required String title,
    required String message,
  }) {
    return MaterialPageRoute(
      builder: (_) => _PlaceholderPage(
        title: title,
        message: message,
      ),
      settings: settings,
    );
  }

  /// Build a 404 not found route
  static MaterialPageRoute _buildNotFoundRoute(RouteSettings settings) {
    return MaterialPageRoute(
      builder: (_) => const _NotFoundPage(),
      settings: settings,
    );
  }

  /// Navigate to route by name
  static Future<T?> navigateTo<T>(
    BuildContext context,
    String routeName, {
    Object? arguments,
  }) {
    return Navigator.pushNamed<T>(
      context,
      routeName,
      arguments: arguments,
    );
  }

  /// Navigate to route and remove all previous routes
  static Future<T?> navigateAndRemoveUntil<T>(
    BuildContext context,
    String routeName, {
    Object? arguments,
  }) {
    return Navigator.pushNamedAndRemoveUntil<T>(
      context,
      routeName,
      (route) => false,
      arguments: arguments,
    );
  }

  /// Replace current route with new route
  static Future<T?> replaceWith<T>(
    BuildContext context,
    String routeName, {
    Object? arguments,
  }) {
    return Navigator.pushReplacementNamed<T, void>(
      context,
      routeName,
      arguments: arguments,
    );
  }

  /// Pop current route
  static void pop<T>(BuildContext context, [T? result]) {
    Navigator.pop<T>(context, result);
  }

  /// Check if can pop
  static bool canPop(BuildContext context) {
    return Navigator.canPop(context);
  }
}

/// Placeholder page for unimplemented features
class _PlaceholderPage extends StatelessWidget {
  const _PlaceholderPage({
    required this.title,
    required this.message,
  });

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.construction_rounded,
                size: 64,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(height: 24),
              Text(
                message,
                style: Theme.of(context).textTheme.titleLarge,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              Text(
                '功能正在开发中，敬请期待',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context)
                          .colorScheme
                          .onSurface
                          .withOpacity(0.6),
                    ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              ElevatedButton.icon(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.arrow_back_rounded),
                label: const Text('返回'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 404 Not Found page
class _NotFoundPage extends StatelessWidget {
  const _NotFoundPage();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('页面未找到'),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.error_outline_rounded,
                size: 64,
                color: Theme.of(context).colorScheme.error,
              ),
              const SizedBox(height: 24),
              Text(
                '404',
                style: Theme.of(context).textTheme.displayLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: Theme.of(context).colorScheme.error,
                    ),
              ),
              const SizedBox(height: 16),
              Text(
                '页面未找到',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                '您访问的页面不存在或已被移除',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context)
                          .colorScheme
                          .onSurface
                          .withOpacity(0.6),
                    ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              ElevatedButton.icon(
                onPressed: () => AppRouter.navigateAndRemoveUntil(
                  context,
                  Routes.home,
                ),
                icon: const Icon(Icons.home_rounded),
                label: const Text('返回首页'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
