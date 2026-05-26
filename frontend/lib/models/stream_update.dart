/// 流式更新状态模型
class StreamUpdate {
  final String type;
  final String step;
  final String status;
  final String message;
  final double progress;
  final String? contractType;
  final int? riskCount;
  final List<RiskPreview>? risksPreview;
  final bool isComplete;

  StreamUpdate({
    required this.type,
    required this.step,
    required this.status,
    required this.message,
    required this.progress,
    this.contractType,
    this.riskCount,
    this.risksPreview,
    this.isComplete = false,
  });

  factory StreamUpdate.fromJson(Map<String, dynamic> json) {
    return StreamUpdate(
      type: json['type'] ?? 'step',
      step: json['step'] ?? '',
      status: json['status'] ?? 'running',
      message: json['message'] ?? '',
      progress: (json['progress'] ?? 0.0).toDouble(),
      contractType: json['contract_type'],
      riskCount: json['risk_count'],
      risksPreview: (json['risks_preview'] as List?)
          ?.map((r) => RiskPreview(
                clause: r['clause'] ?? '',
                riskLevel: r['risk_level'] ?? 'low',
              ))
          .toList(),
      isComplete: json['type'] == 'result',
    );
  }

  bool get isRunning => status == 'running';
  bool get isDone => status == 'done';
  bool get isError => status == 'error';
}

/// 风险预览（用于流式输出中间结果）
class RiskPreview {
  final String clause;
  final String riskLevel;

  RiskPreview({required this.clause, required this.riskLevel});
}
