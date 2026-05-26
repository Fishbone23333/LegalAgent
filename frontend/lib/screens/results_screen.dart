import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:printing/printing.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import '../services/analyze_provider.dart';
import '../theme/app_theme.dart';
import '../models/analyze_result.dart';
import '../widgets/risk_card.dart';
import '../widgets/document_card.dart';

class ResultsScreen extends StatelessWidget {
  const ResultsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AnalyzeProvider>();
    final result = provider.result;

    if (result == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('分析结果')),
        body: const Center(child: Text('无分析结果')),
      );
    }

    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: Text('${result!.contractTypeName}分析报告'),
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: () {
                provider.reset();
                Navigator.popUntil(context, (route) => route.isFirst);
              },
            ),
          ],
          bottom: const TabBar(
            labelColor: Colors.white,
            unselectedLabelColor: Colors.white70,
            indicatorColor: Colors.white,
            tabs: [
              Tab(text: '风险分析', icon: Icon(Icons.warning_amber)),
              Tab(text: '修订建议', icon: Icon(Icons.edit_document)),
              Tab(text: '交涉工具', icon: Icon(Icons.chat_bubble)),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _RiskTab(result: result),
            _RevisionTab(result: result),
            _NegotiationTab(result: result),
          ],
        ),
      ),
    );
  }
}

/// 风险分析Tab
class _RiskTab extends StatelessWidget {
  final AnalyzeResult result;

  const _RiskTab({required this.result});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 风险概览
          _RiskOverview(result: result),
          const SizedBox(height: 16),
          
          // 风险列表
          if (result.risks.isEmpty)
            _NoRiskCard()
          else
            ...result.risks.map((risk) => RiskCard(risk: risk)),
          
          const SizedBox(height: 16),
          
          // 证据清单
          if (result.finalDocuments.evidenceChecklist.isNotEmpty) ...[
            const Text(
              '维权证据清单',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            ...result.finalDocuments.evidenceChecklist
                .map((e) => _EvidenceCard(item: e)),
          ],
        ],
      ),
    );
  }
}

/// 修订建议Tab（双栏对比视图）
class _RevisionTab extends StatelessWidget {
  final AnalyzeResult result;

  const _RevisionTab({required this.result});

  @override
  Widget build(BuildContext context) {
    if (result.finalDocuments.revisionSuggestions.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.check_circle, size: 64, color: Colors.green),
            SizedBox(height: 16),
            Text('本合同未发现明显违规条款'),
            SizedBox(height: 8),
            Text(
              '建议签署前仔细阅读每一条款',
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '合同修订建议表',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '以下为建议修改的条款对比',
            style: TextStyle(color: Colors.grey.shade600),
          ),
          const SizedBox(height: 16),
          
          // 双栏对比视图
          ...result.finalDocuments.revisionSuggestions.asMap().entries.map(
            (entry) => _ComparisonCard(
              index: entry.key + 1,
              suggestion: entry.value,
            ),
          ),
          
          const SizedBox(height: 24),
          
          // 导出按钮
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => _exportPdf(context),
              icon: const Icon(Icons.picture_as_pdf),
              label: const Text('导出PDF修订版'),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _exportPdf(BuildContext context) async {
    final pdf = pw.Document();
    
    pdf.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        build: (context) => [
          pw.Header(
            level: 0,
            child: pw.Text('合同修订建议表',
                style: pw.TextStyle(fontWeight: pw.FontWeight.bold)),
          ),
          pw.SizedBox(height: 20),
          ...result.finalDocuments.revisionSuggestions.map(
            (s) => pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.start,
              children: [
                pw.Text('原文: ${s.originalClause}'),
                pw.Text('建议修改: ${s.suggestedRevision}'),
                pw.Text('理由: ${s.reason}'),
                pw.Divider(),
                pw.SizedBox(height: 10),
              ],
            ),
          ),
        ],
      ),
    );

    await Printing.layoutPdf(
      onLayout: (format) async => pdf.save(),
      name: '合同修订建议',
    );
  }
}

/// 交涉工具Tab
class _NegotiationTab extends StatelessWidget {
  final AnalyzeResult result;

  const _NegotiationTab({required this.result});

  @override
  Widget build(BuildContext context) {
    final script = result.finalDocuments.negotiationScript;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '交涉话术模版',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '高情商谈判版本，可直接使用',
            style: TextStyle(color: Colors.grey.shade600),
          ),
          const SizedBox(height: 16),
          
          // 话术卡片
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.blue.shade50,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.blue.shade100),
            ),
            child: SelectableText(
              script,
              style: const TextStyle(
                fontSize: 14,
                height: 1.6,
              ),
            ),
          ),
          
          const SizedBox(height: 24),
          
          // 一键复制按钮
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () {
                Clipboard.setData(ClipboardData(text: script));
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('已复制到剪贴板'),
                    backgroundColor: Colors.green,
                  ),
                );
              },
              icon: const Icon(Icons.copy),
              label: const Text('一键复制交涉邮件'),
            ),
          ),
          
          const SizedBox(height: 12),
          
          // 分享按钮
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => Share.share(script),
              icon: const Icon(Icons.share),
              label: const Text('分享给朋友'),
            ),
          ),
          
          const SizedBox(height: 24),
          
          // 行动建议
          if (result.actionPlans.isNotEmpty) ...[
            const Text(
              '行动优先级',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            ...result.actionPlans.asMap().entries.map(
              (e) => _ActionCard(index: e.key + 1, action: e.value),
            ),
          ],
        ],
      ),
    );
  }
}

/// 风险概览卡片
class _RiskOverview extends StatelessWidget {
  final AnalyzeResult result;

  const _RiskOverview({required this.result});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  result.criticalRiskCount > 0
                      ? Icons.error
                      : Icons.check_circle,
                  color: result.criticalRiskCount > 0
                      ? AppTheme.criticalColor
                      : AppTheme.lowRiskColor,
                  size: 32,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        result.criticalRiskCount > 0
                            ? '发现 ${result.risks.length} 个风险点'
                            : '合同基本合规',
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        result.contractTypeName,
                        style: TextStyle(color: Colors.grey.shade600),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _RiskCountBadge(
                  label: '致命',
                  count: result.criticalRiskCount,
                  color: AppTheme.criticalColor,
                ),
                _RiskCountBadge(
                  label: '高危',
                  count: result.highRiskCount,
                  color: AppTheme.highRiskColor,
                ),
                _RiskCountBadge(
                  label: '中危',
                  count: result.risks
                      .where((r) => r.riskLevel == 'medium')
                      .length,
                  color: AppTheme.mediumRiskColor,
                ),
                _RiskCountBadge(
                  label: '低危',
                  count: result.risks
                      .where((r) => r.riskLevel == 'low')
                      .length,
                  color: AppTheme.lowRiskColor,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _RiskCountBadge extends StatelessWidget {
  final String label;
  final int count;
  final Color color;

  const _RiskCountBadge({
    required this.label,
    required this.count,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            count.toString(),
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(label, style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
      ],
    );
  }
}

/// 无风险卡片
class _NoRiskCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Card(
      color: Colors.green.shade50,
      child: const Padding(
        padding: EdgeInsets.all(24),
        child: Column(
          children: [
            Icon(Icons.verified, size: 48, color: Colors.green),
            SizedBox(height: 12),
            Text(
              '未发现明显违法条款',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.green,
              ),
            ),
            SizedBox(height: 8),
            Text(
              '本合同条款符合相关法律规定',
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
}

/// 证据卡片
class _EvidenceCard extends StatelessWidget {
  final EvidenceItem item;

  const _EvidenceCard({required this.item});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.blue.shade50,
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Icon(Icons.folder, color: Colors.blue),
        ),
        title: Text(item.evidence),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('获取方式: ${item.howToObtain}'),
            Text('注意: ${item.note}', style: const TextStyle(fontSize: 12)),
          ],
        ),
        isThreeLine: true,
      ),
    );
  }
}

/// 双栏对比卡片
class _ComparisonCard extends StatelessWidget {
  final int index;
  final RevisionSuggestion suggestion;

  const _ComparisonCard({
    required this.index,
    required this.suggestion,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '第 $index 项修订',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: Colors.grey.shade700,
              ),
            ),
            const SizedBox(height: 12),
            
            // 双栏对比
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // 原文（左侧，红色边框）
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.red.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.red.shade200),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.close, 
                                   size: 16, 
                                   color: Colors.red.shade700),
                              const SizedBox(width: 4),
                              Text(
                                '原文（问题）',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.red.shade700,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Expanded(
                            child: SingleChildScrollView(
                              child: Text(
                                suggestion.originalClause,
                                style: const TextStyle(fontSize: 13),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  
                  const SizedBox(width: 8),
                  
                  // 修订（右侧，绿色边框）
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.green.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.green.shade200),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.check,
                                   size: 16,
                                   color: Colors.green.shade700),
                              const SizedBox(width: 4),
                              Text(
                                '建议修改',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.green.shade700,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Expanded(
                            child: SingleChildScrollView(
                              child: Text(
                                suggestion.suggestedRevision,
                                style: const TextStyle(fontSize: 13),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: 8),
            
            // 修订理由
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.lightbulb_outline, size: 16, color: Colors.amber),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      suggestion.reason,
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey.shade700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 行动卡片
class _ActionCard extends StatelessWidget {
  final int index;
  final String action;

  const _ActionCard({
    required this.index,
    required this.action,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: AppTheme.primaryColor,
          child: Text(
            index.toString(),
            style: const TextStyle(color: Colors.white),
          ),
        ),
        title: Text(action),
      ),
    );
  }
}
