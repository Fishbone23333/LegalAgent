import 'package:flutter/material.dart';

/// 合同文本输入组件
class ContractInput extends StatelessWidget {
  final TextEditingController controller;
  final int minLines;
  final int maxLines;

  const ContractInput({
    super.key,
    required this.controller,
    this.minLines = 15,
    this.maxLines = 25,
  });

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      maxLines: maxLines,
      minLines: minLines,
      decoration: InputDecoration(
        hintText: '请粘贴合同文本...\n\n支持劳动合同、租赁合同等各类合同文本。\n\n示例：\n甲方：XXX公司\n乙方：XXX\n合同期限：XXX\n...',
        hintStyle: TextStyle(
          color: Colors.grey.shade400,
          fontSize: 14,
        ),
        alignLabelWithHint: true,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        filled: true,
        fillColor: Colors.white,
      ),
      style: const TextStyle(
        fontSize: 14,
        height: 1.5,
      ),
      textInputAction: TextInputAction.newline,
    );
  }
}
