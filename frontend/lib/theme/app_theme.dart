import 'package:flutter/material.dart';

/// 应用主题
class AppTheme {
  // 品牌色
  static const Color primaryColor = Color(0xFF1E88E5);
  static const Color accentColor = Color(0xFF00ACC1);
  
  // 风险等级颜色
  static const Color criticalColor = Color(0xFFD32F2F);
  static const Color highRiskColor = Color(0xFFF57C00);
  static const Color mediumRiskColor = Color(0xFFFBC02D);
  static const Color lowRiskColor = Color(0xFF4CAF50);
  
  // 背景色
  static const Color backgroundColor = Color(0xFFF5F5F5);
  static const Color cardColor = Colors.white;
  
  // 文字颜色
  static const Color textPrimary = Color(0xFF212121);
  static const Color textSecondary = Color(0xFF757575);
  static const Color textHint = Color(0xFFBDBDBD);

  /// 获取风险等级颜色
  static Color getRiskColor(String riskLevel) {
    switch (riskLevel) {
      case 'critical':
        return criticalColor;
      case 'high':
        return highRiskColor;
      case 'medium':
        return mediumRiskColor;
      default:
        return lowRiskColor;
    }
  }

  /// 获取风险等级图标
  static IconData getRiskIcon(String riskLevel) {
    switch (riskLevel) {
      case 'critical':
        return Icons.error;
      case 'high':
        return Icons.warning;
      case 'medium':
        return Icons.info;
      default:
        return Icons.check_circle;
    }
  }

  /// 获取风险等级中文名
  static String getRiskName(String riskLevel) {
    switch (riskLevel) {
      case 'critical':
        return '致命风险';
      case 'high':
        return '高风险';
      case 'medium':
        return '中风险';
      default:
        return '低风险';
    }
  }

  /// 浅色主题
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primaryColor,
        brightness: Brightness.light,
      ),
      scaffoldBackgroundColor: backgroundColor,
      cardTheme: const CardTheme(
        color: cardColor,
        elevation: 2,
        margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: primaryColor,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Colors.grey),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.grey.shade300),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primaryColor, width: 2),
        ),
        contentPadding: const EdgeInsets.all(16),
      ),
    );
  }
}
