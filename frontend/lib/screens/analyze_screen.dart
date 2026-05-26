import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/analyze_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/analysis_progress.dart';
import '../widgets/contract_input.dart';

class AnalyzeScreen extends StatefulWidget {
  const AnalyzeScreen({super.key});

  @override
  State<AnalyzeScreen> createState() => _AnalyzeScreenState();
}

class _AnalyzeScreenState extends State<AnalyzeScreen> {
  final TextEditingController _contractController = TextEditingController();
  
  @override
  void dispose() {
    _contractController.dispose();
    super.dispose();
  }

  void _startAnalysis() {
    final text = _contractController.text.trim();
    if (text.length < 20) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('请输入完整的合同文本（至少20字符）'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }
    
    context.read<AnalyzeProvider>().analyzeContract(text);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('合同分析'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            context.read<AnalyzeProvider>().reset();
            Navigator.pop(context);
          },
        ),
      ),
      body: Consumer<AnalyzeProvider>(
        builder: (context, provider, _) {
          if (provider.isLoading) {
            return const AnalysisProgress();
          }
          
          if (provider.hasError) {
            return _buildErrorView(provider);
          }
          
          if (provider.hasResult) {
            // 分析完成，跳转到结果页
            WidgetsBinding.instance.addPostFrameCallback((_) {
              Navigator.pushReplacementNamed(context, '/results');
            });
            return const Center(child: CircularProgressIndicator());
          }
          
          return _buildInputView();
        },
      ),
    );
  }

  Widget _buildInputView() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 提示卡片
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.primaryColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: AppTheme.primaryColor.withOpacity(0.3),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.info_outline, color: AppTheme.primaryColor),
                    const SizedBox(width: 8),
                    const Text(
                      '使用提示',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                _buildTipItem('粘贴完整的合同文本或条款'),
                _buildTipItem('支持劳动合同和租赁合同'),
                _buildTipItem('AI将分析风险并生成应对建议'),
              ],
            ),
          ),
          const SizedBox(height: 24),
          
          // 输入框
          const Text(
            '合同文本',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          ContractInput(controller: _contractController),
          
          const SizedBox(height: 24),
          
          // 快捷模板按钮
          const Text(
            '快捷模板',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _TemplateChip(
                label: '劳动合同示例',
                onTap: () => _contractController.text = _employmentContractSample,
              ),
              _TemplateChip(
                label: '租赁合同示例',
                onTap: () => _contractController.text = _housingContractSample,
              ),
            ],
          ),
          
          const SizedBox(height: 32),
          
          // 分析按钮
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _startAnalysis,
              icon: const Icon(Icons.search),
              label: const Text(
                '开始分析',
                style: TextStyle(fontSize: 16),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTipItem(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          const Text('• ', style: TextStyle(fontSize: 14)),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorView(AnalyzeProvider provider) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.red,
            ),
            const SizedBox(height: 16),
            Text(
              provider.errorMessage ?? '分析失败',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 16),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => provider.reset(),
              child: const Text('重新分析'),
            ),
          ],
        ),
      ),
    );
  }

  // 示例劳动合同
  static const String _employmentContractSample = '''
劳动合同

甲方（用人单位）：某科技有限公司
乙方（劳动者）：张三

一、合同期限
本合同期限为3年，自2024年1月1日起至2026年12月31日止。试用期为6个月。

二、工作内容
乙方同意在甲方担任工程师职务，工作地点为北京。

三、薪酬福利
月薪为8000元，每月10日前发放。甲方按国家规定为乙方缴纳社会保险。

四、违约金
乙方提前解除合同，应向甲方支付违约金30000元。

五、竞业限制
乙方离职后2年内不得从事与甲方业务相同的工作，否则赔偿50000元。

六、其他约定
乙方自愿放弃加班工资，要求以调休代替。
''';

  // 示例租赁合同
  static const String _housingContractSample = '''
租赁合同

甲方（出租人）：李四
乙方（承租人）：王五

一、租赁房屋
甲方将位于北京市朝阳区某小区房屋出租给乙方使用。

二、租赁期限
租赁期限为1年，自2024年1月1日起至2024年12月31日止。

三、租金及押金
月租金为5000元，押金为15000元（3个月租金）。押金不退。

四、维修责任
房屋内所有设施维修由乙方负责。

五、提前退租
乙方提前退租需支付2个月租金作为违约金。

六、物业费
物业费、网络费由乙方承担。
''';
}

class _TemplateChip extends StatelessWidget {
  final String label;
  final VoidCallback onTap;

  const _TemplateChip({
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      label: Text(label),
      onPressed: onTap,
      backgroundColor: Colors.grey.shade200,
    );
  }
}
