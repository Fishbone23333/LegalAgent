import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/analyze_result.dart';
import '../models/stream_update.dart';

/// API服务类
class ApiService {
  // 后端API地址（开发环境使用localhost，生产环境使用实际服务器地址）
  static const String baseUrl = 'http://localhost:8000';

  /// 同步分析合同
  static Future<AnalyzeResult> analyzeContract({
    required String text,
    String userId = 'anonymous',
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/analyze'),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'text': text,
          'user_id': userId,
        }),
      );

      if (response.statusCode == 200) {
        return AnalyzeResult.fromJson(jsonDecode(response.body));
      } else {
        final error = jsonDecode(response.body);
        throw ApiException(
          error['detail'] ?? '分析失败',
          statusCode: response.statusCode,
        );
      }
    } on http.ClientException catch (e) {
      throw ApiException('网络连接失败: ${e.message}');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('请求失败: $e');
    }
  }

  /// 流式分析合同
  static Stream<StreamUpdate> analyzeContractStream({
    required String text,
    String userId = 'anonymous',
  }) async* {
    try {
      final request = http.Request(
        'POST',
        Uri.parse('$baseUrl/analyze/stream'),
      );
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode({
        'text': text,
        'user_id': userId,
      });

      final streamedResponse = await request.send();
      
      if (streamedResponse.statusCode == 200) {
        await for (final chunk in streamedResponse.stream
            .transform(utf8.decoder)
            .transform(const LineSplitter())) {
          if (chunk.trim().isNotEmpty) {
            try {
              final json = jsonDecode(chunk);
              yield StreamUpdate.fromJson(json);
            } catch (_) {
              // 忽略解析错误
            }
          }
        }
      } else {
        yield StreamUpdate(
          type: 'error',
          step: 'request',
          status: 'error',
          message: '请求失败: ${streamedResponse.statusCode}',
          progress: 1.0,
        );
      }
    } on http.ClientException catch (e) {
      yield StreamUpdate(
        type: 'error',
        step: 'network',
        status: 'error',
        message: '网络连接失败: ${e.message}',
        progress: 1.0,
      );
    } catch (e) {
      yield StreamUpdate(
        type: 'error',
        step: 'unknown',
        status: 'error',
        message: '请求失败: $e',
        progress: 1.0,
      );
    }
  }

  /// 健康检查
  static Future<bool> healthCheck() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/health'));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}

/// API异常
class ApiException implements Exception {
  final String message;
  final int? statusCode;

  ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}
