import 'package:flutter/material.dart';
import '../models/analyze_result.dart';
import '../models/stream_update.dart';
import '../services/api_service.dart';

/// 合同分析状态管理
class AnalyzeProvider extends ChangeNotifier {
  // 当前状态
  ContractAnalysisState _state = ContractAnalysisState.initial;
  
  // 分析结果
  AnalyzeResult? _result;
  
  // 流式进度
  double _progress = 0.0;
  String _currentStep = '';
  String _statusMessage = '';
  
  // 错误信息
  String? _errorMessage;
  
  // 原始合同文本
  String _rawContract = '';
  
  // 风险预览（流式中间结果）
  List<RiskPreview> _riskPreviews = [];

  // Getters
  ContractAnalysisState get state => _state;
  AnalyzeResult? get result => _result;
  double get progress => _progress;
  String get currentStep => _currentStep;
  String get statusMessage => _statusMessage;
  String? get errorMessage => _errorMessage;
  String get rawContract => _rawContract;
  List<RiskPreview> get riskPreviews => _riskPreviews;

  bool get isLoading => _state == ContractAnalysisState.analyzing;
  bool get hasResult => _result != null;
  bool get hasError => _errorMessage != null;

  /// 执行合同分析
  Future<void> analyzeContract(String text, {String userId = 'anonymous'}) async {
    if (text.trim().length < 20) {
      _errorMessage = '合同文本过短，请提供完整的合同内容（至少20字符）';
      _state = ContractAnalysisState.error;
      notifyListeners();
      return;
    }

    _rawContract = text;
    _state = ContractAnalysisState.analyzing;
    _result = null;
    _errorMessage = null;
    _progress = 0.0;
    _currentStep = '';
    _statusMessage = '正在连接服务器...';
    _riskPreviews = [];
    notifyListeners();

    try {
      // 使用流式API
      await for (final update
          in ApiService.analyzeContractStream(text: text, userId: userId)) {
        _updateFromStream(update);

        if (update.isComplete || update.type == 'result') {
          // 流结束后，获取完整结果
          await _fetchFullResult(text, userId);
          break;
        }

        if (update.isError) {
          _errorMessage = update.message;
          _state = ContractAnalysisState.error;
          notifyListeners();
          return;
        }

        notifyListeners();
      }
    } on ApiException catch (e) {
      _errorMessage = e.message;
      _state = ContractAnalysisState.error;
      notifyListeners();
    } catch (e) {
      _errorMessage = '分析失败: $e';
      _state = ContractAnalysisState.error;
      notifyListeners();
    }
  }

  void _updateFromStream(StreamUpdate update) {
    _progress = update.progress;
    _currentStep = update.step;
    _statusMessage = update.message;
    
    if (update.risksPreview != null) {
      _riskPreviews = update.risksPreview!;
    }
  }

  Future<void> _fetchFullResult(String text, String userId) async {
    try {
      _result = await ApiService.analyzeContract(
        text: text,
        userId: userId,
      );

      if (_result!.success) {
        _state = ContractAnalysisState.completed;
        _progress = 1.0;
        _statusMessage = '分析完成';
      } else {
        _errorMessage = _result!.errorMessage;
        _state = ContractAnalysisState.error;
      }
    } catch (e) {
      _state = ContractAnalysisState.completed;
    }
    notifyListeners();
  }

  /// 重置状态
  void reset() {
    _state = ContractAnalysisState.initial;
    _result = null;
    _errorMessage = null;
    _progress = 0.0;
    _currentStep = '';
    _statusMessage = '';
    _rawContract = '';
    _riskPreviews = [];
    notifyListeners();
  }
}

/// 分析状态枚举
enum ContractAnalysisState {
  initial,   // 初始状态
  analyzing, // 分析中
  completed, // 完成
  error,     // 错误
}
