import 'package:flutter/material.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';

/// Enhanced loading indicators with multiple styles
/// Provides various loading animations for different contexts
class LoadingIndicator extends StatelessWidget {
  final LoadingStyle style;
  final Color? color;
  final double size;
  final String? message;

  const LoadingIndicator({
    super.key,
    this.style = LoadingStyle.spinner,
    this.color,
    this.size = 50.0,
    this.message,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final loadingColor = color ?? theme.colorScheme.primary;

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildIndicator(loadingColor),
          if (message != null) ...[
            const SizedBox(height: 16),
            Text(
              message!,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.textTheme.bodySmall?.color,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildIndicator(Color color) {
    switch (style) {
      case LoadingStyle.spinner:
        return SpinKitFadingCircle(
          color: color,
          size: size,
        );

      case LoadingStyle.pulse:
        return SpinKitPulse(
          color: color,
          size: size,
        );

      case LoadingStyle.wave:
        return SpinKitWave(
          color: color,
          size: size * 0.6,
        );

      case LoadingStyle.dots:
        return SpinKitThreeBounce(
          color: color,
          size: size * 0.4,
        );

      case LoadingStyle.ripple:
        return SpinKitRipple(
          color: color,
          size: size,
        );

      case LoadingStyle.circle:
        return SizedBox(
          width: size,
          height: size,
          child: CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(color),
            strokeWidth: 3,
          ),
        );

      case LoadingStyle.linear:
        return SizedBox(
          width: size * 2,
          child: LinearProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(color),
          ),
        );
    }
  }
}

/// Loading styles for different contexts
enum LoadingStyle {
  spinner, // Default rotating circle
  pulse, // Pulsing circle
  wave, // Wave animation
  dots, // Three bouncing dots
  ripple, // Ripple effect
  circle, // Material circular progress
  linear, // Material linear progress
}

/// Fullscreen loading overlay
class LoadingOverlay extends StatelessWidget {
  final Widget child;
  final bool isLoading;
  final String? message;
  final LoadingStyle style;
  final Color? backgroundColor;

  const LoadingOverlay({
    super.key,
    required this.child,
    required this.isLoading,
    this.message,
    this.style = LoadingStyle.spinner,
    this.backgroundColor,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        child,
        if (isLoading)
          Container(
            color: backgroundColor ??
                Theme.of(context).colorScheme.surface.withOpacity(0.8),
            child: LoadingIndicator(
              style: style,
              message: message,
            ),
          ),
      ],
    );
  }
}

/// Small inline loading indicator
class InlineLoadingIndicator extends StatelessWidget {
  final Color? color;
  final double size;

  const InlineLoadingIndicator({
    super.key,
    this.color,
    this.size = 16.0,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CircularProgressIndicator(
        valueColor: AlwaysStoppedAnimation<Color>(
          color ?? Theme.of(context).colorScheme.primary,
        ),
        strokeWidth: 2,
      ),
    );
  }
}

/// Button loading state
class LoadingButton extends StatelessWidget {
  final VoidCallback? onPressed;
  final Widget child;
  final bool isLoading;
  final ButtonStyle? style;
  final double loadingSize;

  const LoadingButton({
    super.key,
    required this.onPressed,
    required this.child,
    required this.isLoading,
    this.style,
    this.loadingSize = 20.0,
  });

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: isLoading ? null : onPressed,
      style: style,
      child: isLoading
          ? SizedBox(
              width: loadingSize,
              height: loadingSize,
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(
                  Theme.of(context).colorScheme.onPrimary,
                ),
                strokeWidth: 2,
              ),
            )
          : child,
    );
  }
}

/// Progress bar with percentage
class ProgressBar extends StatelessWidget {
  final double progress; // 0.0 to 1.0
  final String? label;
  final bool showPercentage;
  final Color? backgroundColor;
  final Color? progressColor;
  final double height;

  const ProgressBar({
    super.key,
    required this.progress,
    this.label,
    this.showPercentage = true,
    this.backgroundColor,
    this.progressColor,
    this.height = 8.0,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final percentage = (progress * 100).toInt();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (label != null || showPercentage) ...[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              if (label != null)
                Text(
                  label!,
                  style: theme.textTheme.bodySmall,
                ),
              if (showPercentage)
                Text(
                  '$percentage%',
                  style: theme.textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
        ],
        ClipRRect(
          borderRadius: BorderRadius.circular(height / 2),
          child: SizedBox(
            height: height,
            child: LinearProgressIndicator(
              value: progress,
              backgroundColor: backgroundColor ??
                  theme.colorScheme.surfaceVariant,
              valueColor: AlwaysStoppedAnimation<Color>(
                progressColor ?? theme.colorScheme.primary,
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// Circular progress with percentage
class CircularProgress extends StatelessWidget {
  final double progress; // 0.0 to 1.0
  final double size;
  final Color? backgroundColor;
  final Color? progressColor;
  final bool showPercentage;
  final double strokeWidth;

  const CircularProgress({
    super.key,
    required this.progress,
    this.size = 60.0,
    this.backgroundColor,
    this.progressColor,
    this.showPercentage = true,
    this.strokeWidth = 4.0,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final percentage = (progress * 100).toInt();

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CircularProgressIndicator(
            value: progress,
            strokeWidth: strokeWidth,
            backgroundColor: backgroundColor ??
                theme.colorScheme.surfaceVariant,
            valueColor: AlwaysStoppedAnimation<Color>(
              progressColor ?? theme.colorScheme.primary,
            ),
          ),
          if (showPercentage)
            Text(
              '$percentage%',
              style: theme.textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
        ],
      ),
    );
  }
}

/// Skeleton loader for content placeholder
class SkeletonLoader extends StatelessWidget {
  final double width;
  final double height;
  final BorderRadius? borderRadius;

  const SkeletonLoader({
    super.key,
    this.width = double.infinity,
    this.height = 16.0,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: borderRadius ?? BorderRadius.circular(4),
      ),
    );
  }
}
