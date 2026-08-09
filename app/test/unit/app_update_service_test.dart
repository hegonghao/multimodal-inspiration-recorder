import 'package:flutter_test/flutter_test.dart';
import 'package:multimodal_inspiration_recorder/data/services/app_update_service.dart';

void main() {
  AppUpdateInfo update({
    required String currentVersion,
    required int currentBuild,
    required String latestVersion,
    required int latestBuild,
  }) {
    return AppUpdateInfo(
      currentVersion: currentVersion,
      currentBuild: currentBuild,
      latestVersion: latestVersion,
      latestBuild: latestBuild,
      downloadUrl: 'https://example.com/app.apk',
      releaseNotes: '',
      forceUpdate: false,
    );
  }

  test('detects a newer build number', () {
    final result = update(
      currentVersion: '1.0.0',
      currentBuild: 1,
      latestVersion: '1.0.0',
      latestBuild: 2,
    );

    expect(result.hasUpdate, isTrue);
  });

  test('detects a newer semantic version', () {
    final result = update(
      currentVersion: '1.0.9',
      currentBuild: 10,
      latestVersion: '1.1.0',
      latestBuild: 10,
    );

    expect(result.hasUpdate, isTrue);
  });

  test('does not report the installed build as an update', () {
    final result = update(
      currentVersion: '1.0.1',
      currentBuild: 2,
      latestVersion: '1.0.1',
      latestBuild: 2,
    );

    expect(result.hasUpdate, isFalse);
  });
}
