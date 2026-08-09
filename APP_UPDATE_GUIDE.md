# 手机端更新

该项目的 Android 更新流程为：手机端从 `/api/v1/health/version` 获取版本信息，下载服务器返回的 APK，并打开 Android 系统安装器。系统仍会要求用户确认安装，这是 Android 的安全限制。

## 发布新版本

1. 修改 `app/pubspec.yaml` 的 `version`，例如 `1.0.1+2`。
2. 构建 APK：

```powershell
cd app
flutter build apk --release
```

3. 将生成的 `app/build/app/outputs/flutter-apk/app-release.apk` 上传到一个手机可访问的 HTTPS 地址，例如 GitHub Release。
4. 在服务器根目录 `.env` 设置：

```dotenv
MOBILE_APP_VERSION=1.0.1
MOBILE_APP_BUILD=2
MOBILE_APP_APK_URL=https://example.com/downloads/app-release.apk
MOBILE_APP_RELEASE_NOTES=修复同步和删除问题
MOBILE_APP_FORCE_UPDATE=false
```

5. 更新后端：

```bash
docker compose up -d --build --force-recreate backend worker
```

## 手机端使用

安装一次带有更新功能的版本后，在“设置 -> 应用更新”点击即可检查并下载新 APK。首次增加这个功能仍需要手动安装 `1.0.1+2`，后续版本无需连接电脑重装。

## 签名要求

正式发布应使用固定的 Android release keystore。后续 APK 必须使用同一签名，否则 Android 会拒绝覆盖安装，用户需要先卸载旧应用并会丢失本地数据。
