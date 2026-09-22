import 'dart:math';
import 'package:flutter/material.dart';
import '../models/diagram_model.dart';
import '../core/theme/app_theme.dart';

class UMLRelationshipPainter extends CustomPainter {
  final List<DiagramNodeModel> nodes;
  final List<DiagramEdgeModel> edges;

  UMLRelationshipPainter({
    required this.nodes,
    required this.edges,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (nodes.isEmpty || edges.isEmpty) return;

    final nodeMap = {for (var n in nodes) n.id: n};

    final linePaint = Paint()
      ..color = AppTheme.textSecondary
      ..strokeWidth = 1.6
      ..style = PaintingStyle.stroke;

    final fillPaint = Paint()
      ..color = AppTheme.textSecondary
      ..style = PaintingStyle.fill;

    final hollowPaint = Paint()
      ..color = AppTheme.surface1
      ..style = PaintingStyle.fill;

    for (final edge in edges) {
      final source = nodeMap[edge.sourceId];
      final target = nodeMap[edge.targetId];

      if (source == null || target == null) continue;

      // Centers
      final sCenter = Offset(source.x + source.width / 2, source.y + source.height / 2);
      final tCenter = Offset(target.x + target.width / 2, target.y + target.height / 2);

      // Intersect with source box and target box
      final sPoint = _getBoxIntersection(sCenter, tCenter, source);
      final tPoint = _getBoxIntersection(tCenter, sCenter, target);

      final relType = edge.type.toLowerCase();

      // Draw line
      if (relType == 'dependency' || relType == 'realization') {
        _drawDashedLine(canvas, sPoint, tPoint, linePaint);
      } else {
        canvas.drawLine(sPoint, tPoint, linePaint);
      }

      // Draw markers based on relationship type
      final angle = atan2(tPoint.dy - sPoint.dy, tPoint.dx - sPoint.dx);

      switch (relType) {
        case 'inheritance':
        case 'realization':
          // Hollow triangle at target
          _drawTriangleMarker(canvas, tPoint, angle, linePaint, hollowPaint);
          break;

        case 'composition':
          // Filled diamond at source
          _drawDiamondMarker(canvas, sPoint, angle + pi, linePaint, fillPaint);
          break;

        case 'aggregation':
          // Hollow diamond at source
          _drawDiamondMarker(canvas, sPoint, angle + pi, linePaint, hollowPaint);
          break;

        case 'association':
        case 'dependency':
        default:
          // Open arrow at target
          _drawOpenArrow(canvas, tPoint, angle, linePaint);
          break;
      }

      // Edge label if present
      if (edge.label != null && edge.label!.isNotEmpty) {
        final midPoint = Offset((sPoint.dx + tPoint.dx) / 2, (sPoint.dy + tPoint.dy) / 2 - 12);
        final textSpan = TextSpan(
          text: edge.label!,
          style: const TextStyle(
            color: AppTheme.textSecondary,
            fontSize: 10,
            backgroundColor: AppTheme.surface1,
          ),
        );
        final textPainter = TextPainter(
          text: textSpan,
          textDirection: TextDirection.ltr,
        )..layout();
        textPainter.paint(canvas, midPoint - Offset(textPainter.width / 2, textPainter.height / 2));
      }
    }
  }

  Offset _getBoxIntersection(Offset center, Offset target, DiagramNodeModel node) {
    final dx = target.dx - center.dx;
    final dy = target.dy - center.dy;

    if (dx == 0 && dy == 0) return center;

    final halfW = node.width / 2;
    final halfH = node.height / 2;

    final scaleX = dx.abs() > 0.001 ? halfW / dx.abs() : 9999.0;
    final scaleY = dy.abs() > 0.001 ? halfH / dy.abs() : 9999.0;

    final scale = min(scaleX, scaleY);
    return Offset(center.dx + dx * scale, center.dy + dy * scale);
  }

  void _drawDashedLine(Canvas canvas, Offset p1, Offset p2, Paint paint) {
    const dashWidth = 5.0;
    const dashSpace = 4.0;
    final distance = (p2 - p1).distance;
    final unitVector = (p2 - p1) / distance;

    double currentDistance = 0;
    while (currentDistance < distance) {
      final start = p1 + unitVector * currentDistance;
      final endDistance = min(currentDistance + dashWidth, distance);
      final end = p1 + unitVector * endDistance;
      canvas.drawLine(start, end, paint);
      currentDistance += dashWidth + dashSpace;
    }
  }

  void _drawTriangleMarker(Canvas canvas, Offset tip, double angle, Paint stroke, Paint fill) {
    const size = 12.0;
    final path = Path();
    path.moveTo(tip.dx, tip.dy);
    path.lineTo(
      tip.dx - size * cos(angle - pi / 6),
      tip.dy - size * sin(angle - pi / 6),
    );
    path.lineTo(
      tip.dx - size * cos(angle + pi / 6),
      tip.dy - size * sin(angle + pi / 6),
    );
    path.close();

    canvas.drawPath(path, fill);
    canvas.drawPath(path, stroke);
  }

  void _drawDiamondMarker(Canvas canvas, Offset tip, double angle, Paint stroke, Paint fill) {
    const length = 14.0;
    const width = 8.0;

    final p1 = tip;
    final p2 = Offset(tip.dx - (length / 2) * cos(angle) + (width / 2) * sin(angle),
        tip.dy - (length / 2) * sin(angle) - (width / 2) * cos(angle));
    final p3 = Offset(tip.dx - length * cos(angle), tip.dy - length * sin(angle));
    final p4 = Offset(tip.dx - (length / 2) * cos(angle) - (width / 2) * sin(angle),
        tip.dy - (length / 2) * sin(angle) + (width / 2) * cos(angle));

    final path = Path()
      ..moveTo(p1.dx, p1.dy)
      ..lineTo(p2.dx, p2.dy)
      ..lineTo(p3.dx, p3.dy)
      ..lineTo(p4.dx, p4.dy)
      ..close();

    canvas.drawPath(path, fill);
    canvas.drawPath(path, stroke);
  }

  void _drawOpenArrow(Canvas canvas, Offset tip, double angle, Paint stroke) {
    const size = 10.0;
    canvas.drawLine(
      tip,
      Offset(
        tip.dx - size * cos(angle - pi / 6),
        tip.dy - size * sin(angle - pi / 6),
      ),
      stroke,
    );
    canvas.drawLine(
      tip,
      Offset(
        tip.dx - size * cos(angle + pi / 6),
        tip.dy - size * sin(angle + pi / 6),
      ),
      stroke,
    );
  }

  @override
  bool shouldRepaint(covariant UMLRelationshipPainter oldDelegate) {
    return oldDelegate.nodes != nodes || oldDelegate.edges != edges;
  }
}
