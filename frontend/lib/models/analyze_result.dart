/// 合同分析结果数据模型
class AnalyzeResult {
  final bool success;
  final String contractType;
  final bool isValidContract;
  final List<ContractSegment> segments;
  final List<RiskPoint> risks;
  final List<String> actionPlans;
  final FinalDocuments finalDocuments;
  final String errorMessage;

  AnalyzeResult({
    required this.success,
    required this.contractType,
    required this.isValidContract,
    required this.segments,
    required this.risks,
    required this.actionPlans,
    required this.finalDocuments,
    required this.errorMessage,
  });

  factory AnalyzeResult.fromJson(Map<String, dynamic> json) {
    return AnalyzeResult(
      success: json['success'] ?? false,
      contractType: json['contract_type'] ?? 'unknown',
      isValidContract: json['is_valid_contract'] ?? false,
      segments: (json['segments'] as List?)
              ?.map((s) => ContractSegment.fromJson(s))
              .toList() ??
          [],
      risks: (json['risks'] as List?)
              ?.map((r) => RiskPoint.fromJson(r))
              .toList() ??
          [],
      actionPlans: List<String>.from(json['action_plans'] ?? []),
      finalDocuments:
          FinalDocuments.fromJson(json['final_documents'] ?? {}),
      errorMessage: json['error_message'] ?? '',
    );
  }

  String get contractTypeName {
    switch (contractType) {
      case 'employment':
        return '劳动合同';
      case 'housing':
        return '租赁合同';
      default:
        return '未知类型';
    }
  }

  int get criticalRiskCount =>
      risks.where((r) => r.riskLevel == 'critical').length;

  int get highRiskCount =>
      risks.where((r) => r.riskLevel == 'high').length;
}

/// 合同条款模块
class ContractSegment {
  final String title;
  final String content;
  final Map<String, dynamic> keyItems;

  ContractSegment({
    required this.title,
    required this.content,
    required this.keyItems,
  });

  factory ContractSegment.fromJson(Map<String, dynamic> json) {
    return ContractSegment(
      title: json['title'] ?? '',
      content: json['content'] ?? '',
      keyItems: json['key_items'] ?? {},
    );
  }
}

/// 风险点
class RiskPoint {
  final String clause;
  final String riskLevel;
  final String riskType;
  final String legalBasis;
  final String recommendation;
  final String severityNote;

  RiskPoint({
    required this.clause,
    required this.riskLevel,
    required this.riskType,
    required this.legalBasis,
    required this.recommendation,
    required this.severityNote,
  });

  factory RiskPoint.fromJson(Map<String, dynamic> json) {
    return RiskPoint(
      clause: json['clause'] ?? '',
      riskLevel: json['risk_level'] ?? 'low',
      riskType: json['risk_type'] ?? '',
      legalBasis: json['legal_basis'] ?? '',
      recommendation: json['recommendation'] ?? '',
      severityNote: json['severity_note'] ?? '',
    );
  }

  String get riskLevelName {
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
}

/// 最终生成的法律文书
class FinalDocuments {
  final List<RevisionSuggestion> revisionSuggestions;
  final String negotiationScript;
  final List<EvidenceItem> evidenceChecklist;

  FinalDocuments({
    required this.revisionSuggestions,
    required this.negotiationScript,
    required this.evidenceChecklist,
  });

  factory FinalDocuments.fromJson(Map<String, dynamic> json) {
    return FinalDocuments(
      revisionSuggestions: (json['revision_suggestions'] as List?)
              ?.map((s) => RevisionSuggestion.fromJson(s))
              .toList() ??
          [],
      negotiationScript: json['negotiation_script'] ?? '',
      evidenceChecklist: (json['evidence_checklist'] as List?)
              ?.map((e) => EvidenceItem.fromJson(e))
              .toList() ??
          [],
    );
  }
}

/// 修订建议
class RevisionSuggestion {
  final String originalClause;
  final String suggestedRevision;
  final String reason;

  RevisionSuggestion({
    required this.originalClause,
    required this.suggestedRevision,
    required this.reason,
  });

  factory RevisionSuggestion.fromJson(Map<String, dynamic> json) {
    return RevisionSuggestion(
      originalClause: json['original_clause'] ?? '',
      suggestedRevision: json['suggested_revision'] ?? '',
      reason: json['reason'] ?? '',
    );
  }
}

/// 证据清单项
class EvidenceItem {
  final String evidence;
  final String howToObtain;
  final String note;

  EvidenceItem({
    required this.evidence,
    required this.howToObtain,
    required this.note,
  });

  factory EvidenceItem.fromJson(Map<String, dynamic> json) {
    return EvidenceItem(
      evidence: json['evidence'] ?? '',
      howToObtain: json['how_to_obtain'] ?? '',
      note: json['note'] ?? '',
    );
  }
}
