import 'dart:io';

import 'package:dio/dio.dart';
import 'package:open_filex/open_filex.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:path_provider/path_provider.dart';

import 'api_service.dart';

class AppUpdateInfo {
  const AppUpdateInfo({
    required this.currentVersion,
    required this.currentBuild,
    required this.latestVersion,
    required this.latestBuild,
    required this.downloadUrl,
    required this.releaseNotes,
    required this.forceUpdate,
  });

  final String currentVersion;
  final int currentBuild;
  final String latestVersion;
  final int latestBuild;
  final String? downloadUrl;
  final String releaseNotes;
  final bool forceUpdate;

  bool get hasUpdate =>
      latestBuild > currentBuild ||
      _compareVersions(latestVersion, currentVersion) > 0;

  static int _compareVersions(String left, String right) {
    final leftParts =
        left.split('.').map((part) => int.tryParse(part) ?? 0).toList();
    final rightParts =
        right.split('.').map((part) => int.tryParse(part) ?? 0).toList();
    final length = leftParts.length > rightParts.length
        ? leftParts.length
        : rightParts.length;
    for (var index = 0; index < length; index++) {
      final leftPart = index < leftParts.length ? leftParts[index] : 0;
      final rightPart = index < rightParts.length ? rightParts[index] : 0;
      if (leftPart != rightPart) return leftPart.compareTo(rightPart);
    }
    return 0;
  }
}

class AppUpdateService {
  AppUpdateService({required ApiService apiService}) : _apiService = apiService;

  final ApiService _apiService;

  Future<AppUpdateInfo> checkForUpdate() async {
    final packageInfo = await PackageInfo.fromPlatform();
    final response = await _apiService.getMobileAppVersion();

    return AppUpdateInfo(
      currentVersion: packageInfo.version,
      currentBuild: int.tryParse(packageInfo.buildNumber) ?? 0,
      latestVersion:
          response['latest_version'] as String? ?? packageInfo.version,
      latestBuild: response['latest_build'] as int? ?? 0,
      downloadUrl: response['download_url'] as String?,
      releaseNotes: response['release_notes'] as String? ?? '',
      forceUpdate: response['force_update'] as bool? ?? false,
    );
  }

  Future<String> downloadApk(
    AppUpdateInfo update, {
    void Function(int received, int total)? onProgress,
  }) async {
    if (!Platform.isAndroid) {
      throw UnsupportedError('通过网络安装 APK 仅支持 Android');
    }
    final url = update.downloadUrl;
    if (url == null || url.trim().isEmpty) {
      throw StateError('服务器未配置 APK 下载地址');
    }

    final directory = await getTemporaryDirectory();
    final apkPath =
        '${directory.path}/inspiration-recorder-${update.latestBuild}.apk';
    final dio = Dio();
    await dio.download(url, apkPath, onReceiveProgress: onProgress);
    return apkPath;
  }

  Future<void> installApk(String apkPath) async {
    final result = await OpenFilex.open(
      apkPath,
      type: 'application/vnd.android.package-archive',
    );
    if (result.type != ResultType.done) {
      throw StateError(result.message);
    }
  }
}
