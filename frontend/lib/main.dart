import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/analyze_provider.dart';
import 'theme/app_theme.dart';
import 'screens/home_screen.dart';
import 'screens/analyze_screen.dart';
import 'screens/results_screen.dart';

void main() {
  runApp(const LegalShieldApp());
}

class LegalShieldApp extends StatelessWidget {
  const LegalShieldApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AnalyzeProvider(),
      child: MaterialApp(
        title: '法律护航卫士',
        theme: AppTheme.lightTheme,
        debugShowCheckedModeBanner: false,
        home: const HomeScreen(),
        routes: {
          '/analyze': (context) => const AnalyzeScreen(),
          '/results': (context) => const ResultsScreen(),
        },
      ),
    );
  }
}
