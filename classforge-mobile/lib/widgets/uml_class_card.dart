import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../core/theme/app_theme.dart';
import '../models/diagram_model.dart';

class UMLClassCard extends StatelessWidget {
  final DiagramNodeModel node;
  final VoidCallback? onTap;
  final bool isSelected;

  const UMLClassCard({
    Key? key,
    required this.node,
    this.onTap,
    this.isSelected = false,
  }) : super(key: key);

  Color _getHeaderColor() {
    switch (node.type.toLowerCase()) {
      case 'interface':
        return const Color(0xFF00C896); // Accent green/teal
      case 'abstract':
        return const Color(0xFF7C3AED); // Purple
      case 'enum':
        return const Color(0xFFF5A623); // Amber/orange
      case 'note':
        return const Color(0xFF475569); // Slate
      case 'class':
      default:
        return AppTheme.primary; // 0xFF2D6BE4
    }
  }

  Color _getVisibilityColor(String visibility) {
    switch (visibility) {
      case '+':
        return const Color(0xFF86EFAC); // Light green
      case '-':
        return const Color(0xFFFCA5A5); // Light red
      case '#':
        return const Color(0xFFFCD34D); // Light amber
      case '~':
        return const Color(0xFFA78BFA); // Light purple
      default:
        return AppTheme.textSecondary;
    }
  }

  @override
  Widget build(BuildContext context) {
    final headerColor = _getHeaderColor();

    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: node.width > 0 ? node.width : 200,
        decoration: BoxDecoration(
          color: AppTheme.surface2,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? headerColor : AppTheme.border,
            width: isSelected ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: isSelected
                  ? headerColor.withOpacity(0.3)
                  : Colors.black.withOpacity(0.3),
              blurRadius: isSelected ? 8 : 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: headerColor.withOpacity(0.18),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(7)),
                border: Border(bottom: BorderSide(color: headerColor.withOpacity(0.5))),
              ),
              child: Column(
                children: [
                  if (node.stereotype != null && node.stereotype!.isNotEmpty)
                    Text(
                      '«${node.stereotype}»',
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        color: headerColor,
                        fontStyle: FontStyle.italic,
                        fontWeight: FontWeight.w600,
                      ),
                      textAlign: TextAlign.center,
                    )
                  else if (node.type != 'class')
                    Text(
                      '«${node.type}»',
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        color: headerColor,
                        fontStyle: FontStyle.italic,
                        fontWeight: FontWeight.w600,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  Text(
                    node.name,
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.textPrimary,
                    ),
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),

            // Attributes Section
            if (node.attributes.isNotEmpty)
              Container(
                padding: const EdgeInsets.all(8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: node.attributes.map((attr) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 1.5),
                      child: Row(
                        children: [
                          Text(
                            attr.visibility,
                            style: GoogleFonts.jetBrainsMono(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: _getVisibilityColor(attr.visibility),
                            ),
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              '${attr.name}: ${attr.type}',
                              style: GoogleFonts.jetBrainsMono(
                                fontSize: 10.5,
                                color: AppTheme.textPrimary,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ),
              )
            else
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
                child: Text(
                  'sin atributos',
                  style: GoogleFonts.inter(
                    fontSize: 9.5,
                    color: AppTheme.textMuted,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ),

            // Divider between attributes and methods
            const Divider(height: 1, thickness: 1, color: AppTheme.border),

            // Methods Section
            if (node.methods.isNotEmpty)
              Container(
                padding: const EdgeInsets.all(8),
                decoration: const BoxDecoration(
                  borderRadius: BorderRadius.vertical(bottom: Radius.circular(7)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: node.methods.map((method) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 1.5),
                      child: Row(
                        children: [
                          Text(
                            method.visibility,
                            style: GoogleFonts.jetBrainsMono(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: _getVisibilityColor(method.visibility),
                            ),
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              '${method.name}${method.params}: ${method.returnType}',
                              style: GoogleFonts.jetBrainsMono(
                                fontSize: 10.5,
                                color: AppTheme.textSecondary,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ),
              )
            else
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
                child: Text(
                  'sin métodos',
                  style: GoogleFonts.inter(
                    fontSize: 9.5,
                    color: AppTheme.textMuted,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
