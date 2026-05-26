import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/analyze_provider.dart';
import '../theme/app_theme.dart';

/// 分析进度展示组件
class AnalysisProgress extends StatelessWidget {
  const AnalysisProgress({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AnalyzeProvider>(
      builder: (context, provider, _) {
        return Center(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // 进度环
                  SizedBox(
                    width: 150,
                    height: 150,
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        SizedBox(
                          width: 150,
                          height: 150,
                          child: CircularProgressIndicator(
                            value: provider.progress,
                            strokeWidth: 8,
                            backgroundColor: Colors.grey.shade200,
                            valueColor: const AlwaysStoppedAnimation<Color>(
                              AppTheme.primaryColor,
                            ),
                          ),
                        ),
                        Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              '${(provider.progress * 100).toInt()}%',
                              style: const TextStyle(
                                fontSize: 28,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              _getStepName(provider.currentStep),
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.grey.shade600,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 48),

                  // 步骤列表
                  _StepItem(
                    label: '验证合同文本',
                    isDone: _isStepDone('validating', provider.currentStep),
                    isRunning: _isStepRunning('validating', provider.currentStep),
                  ),
                  _StepConnector(
                    isDone: _isStepDone('validated', provider.currentStep),
                  ),
                  _StepItem(
                    label: '解析合同条款',
                    isDone: _isStepDone('extracting', provider.currentStep),
                    isRunning: _isStepRunning('extracting', provider.currentStep),
                  ),
                  _StepConnector(
                    isDone: _isStepDone('risk_checker', provider.currentStep),
                  ),
                  _StepItem(
                    label: '分析法律风险',
                    isDone: _isStepDone('analyzing_risks', provider.currentStep),
                    isRunning: _isStepRunning('analyzing_risks', provider.currentStep),
                  ),
                  _StepConnector(
                    isDone: _isStepDone('draft_generator', provider.currentStep),
                  ),
                  _StepItem(
                    label: '生成法律文书',
                    isDone: _isStepDone('generating_documents', provider.currentStep),
                    isRunning: _isStepRunning('generating_documents', provider.currentStep),
                  ),

                  const SizedBox(height: 32),

                  // 当前状态消息
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: provider.hasError
                          ? Colors.red.shade50
                          : AppTheme.primaryColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (provider.isLoading)
                          const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        else if (provider.hasError)
                          const Icon(Icons.error, color: Colors.red, size: 16)
                        else
                          const Icon(Icons.check_circle,
                              color: Colors.green, size: 16),
                        const SizedBox(width: 8),
                        Flexible(
                          child: Text(
                            provider.statusMessage,
                            style: TextStyle(
                              color: provider.hasError
                                  ? Colors.red
                                  : AppTheme.textPrimary,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  // 风险预览（流式中间结果）
                  if (provider.riskPreviews.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.orange.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.orange.shade200),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '发现风险点预览',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.orange.shade700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          ...provider.riskPreviews.map(
                            (r) => Padding(
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Row(
                                children: [
                                  Icon(
                                    AppTheme.getRiskIcon(r.riskLevel),
                                    size: 16,
                                    color: AppTheme.getRiskColor(r.riskLevel),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      r.clause,
                                      style: const TextStyle(fontSize: 12),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  bool _isStepDone(String stepName, String currentStep) {
    const order = [
      'validating', 'validated', 'extracting',
      'analyzing_risks', 'generating_documents'
    ];
    final currentIdx = order.indexOf(currentStep);
    final stepIdx = order.indexOf(stepName);
    return currentIdx > stepIdx;
  }

  bool _isStepRunning(String stepName, String currentStep) {
    return currentStep == stepName;
  }

  String _getStepName(String step) {
    const names = {
      'validating': '验证中',
      'validated': '已验证',
      'extracting': '解析中',
      'analyzing_risks': '分析中',
      'generating_documents': '生成中',
    };
    return names[step] ?? '处理中';
  }
}

class _StepItem extends StatelessWidget {
  final String label;
  final bool isDone;
  final bool isRunning;

  const _StepItem({
    required this.label,
    required this.isDone,
    required this.isRunning,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isDone
                ? Colors.green
                : isRunning
                    ? AppTheme.primaryColor
                    : Colors.grey.shade300,
          ),
          child: Center(
            child: isDone
                ? const Icon(Icons.check, color: Colors.white, size: 18)
                : isRunning
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor:
                              AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      )
                    : Text(
                        label[0],
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
          ),
        ),
        const SizedBox(width: 12),
        Text(
          label,
          style: TextStyle(
            fontWeight: isRunning ? FontWeight.bold : FontWeight.normal,
            color: isDone || isRunning ? AppTheme.textPrimary : Colors.grey,
          ),
        ),
      ],
    );
  }
}

class _StepConnector extends StatelessWidget {
  final bool isDone;

  const _StepConnector({required this.isDone});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 2,
      height: 24,
      margin: const EdgeInsets.only(left: 15),
      color: isDone ? Colors.green : Colors.grey.shade300,
    );
  }
}
