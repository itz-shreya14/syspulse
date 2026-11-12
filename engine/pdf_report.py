import io
from datetime import datetime
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether
)

class PDFReportGenerator:
    """
    Generates an executive-ready system diagnostic and telemetry report in PDF format.
    """
    @staticmethod
    def generate(
        telemetry: Dict[str, Any],
        health: Dict[str, Any],
        top_procs: List[Dict[str, Any]],
        network_data: Dict[str, Any]
    ) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0f172a')
        )

        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748b')
        )

        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#0284c7'),
            spaceBefore=10,
            spaceAfter=6
        )

        body_style = ParagraphStyle(
            'BodyText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#334155')
        )

        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#ffffff')
        )

        table_cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#1e293b')
        )

        table_cell_bold = ParagraphStyle(
            'TableCellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0f172a')
        )

        story = []

        # --- 1. Header & Metadata ---
        sys_info = telemetry.get("system", {})
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        story.append(Paragraph("SysPulse System Diagnostic Audit Report", title_style))
        story.append(Spacer(1, 2))
        story.append(Paragraph(
            f"Generated: {now_str} &nbsp;|&nbsp; Target Host: <b>{sys_info.get('hostname', 'Localhost')}</b> &nbsp;|&nbsp; Platform: <b>{sys_info.get('os')} {sys_info.get('os_release')}</b>",
            subtitle_style
        ))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284c7'), spaceAfter=12))

        # --- 2. Executive Health Summary Card ---
        score = health.get("health_score", 100)
        status_text = health.get("status_text", "OPTIMAL")
        score_color = colors.HexColor('#10b981') if score >= 80 else (colors.HexColor('#f59e0b') if score >= 60 else colors.HexColor('#ef4444'))

        summary_data = [
            [
                Paragraph(f"<b>Overall Health Score:</b> <font color='{score_color.hexval()}'><b>{score} / 100</b></font> ({status_text})", body_style),
                Paragraph(f"<b>Uptime:</b> {telemetry.get('uptime_formatted', 'N/A')}", body_style)
            ],
            [
                Paragraph(f"<b>Processor:</b> {sys_info.get('processor', 'N/A')}", body_style),
                Paragraph(f"<b>Cores:</b> {sys_info.get('physical_cores')} Physical / {sys_info.get('logical_cores')} Logical", body_style)
            ]
        ]
        summary_table = Table(summary_data, colWidths=[270, 270])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 10))

        # --- 3. Diagnostic Findings & Warnings ---
        findings = health.get("findings", [])
        if findings:
            story.append(Paragraph("System Doctor Findings & Health Alerts", section_heading))
            findings_data = [[
                Paragraph("Severity", table_header_style),
                Paragraph("Finding", table_header_style),
                Paragraph("Recommendation / Detail", table_header_style)
            ]]

            for f in findings:
                lvl = f.get("level", "info").upper()
                badge_color = "#ef4444" if lvl == "CRITICAL" else ("#f59e0b" if lvl == "WARNING" else "#0284c7")
                findings_data.append([
                    Paragraph(f"<font color='{badge_color}'><b>{lvl}</b></font>", table_cell_bold),
                    Paragraph(f.get("title", ""), table_cell_bold),
                    Paragraph(f.get("message", ""), table_cell_style)
                ])

            findings_table = Table(findings_data, colWidths=[65, 175, 300])
            findings_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(findings_table)
            story.append(Spacer(1, 10))

        # --- 4. Hardware Telemetry Snapshot ---
        story.append(Paragraph("Core Hardware Telemetry Snapshot", section_heading))
        cpu = telemetry.get("cpu", {})
        ram = telemetry.get("memory", {}).get("ram", {})
        swap = telemetry.get("memory", {}).get("swap", {})
        battery = telemetry.get("battery", {})

        freq_str = f"{(cpu.get('current_freq_mhz', 0) / 1000):.2f} GHz" if cpu.get("current_freq_mhz") else "N/A"
        bat_str = f"{battery.get('percent', 'N/A')}% ({battery.get('status_text', 'AC Power')})"

        metrics_data = [
            [
                Paragraph("Subsystem", table_header_style),
                Paragraph("Utilization", table_header_style),
                Paragraph("Details & Allocation", table_header_style)
            ],
            [
                Paragraph("CPU Overall", table_cell_bold),
                Paragraph(f"<b>{cpu.get('overall_percent', 0)}%</b>", table_cell_style),
                Paragraph(f"Clock Speed: {freq_str}", table_cell_style)
            ],
            [
                Paragraph("Memory (RAM)", table_cell_bold),
                Paragraph(f"<b>{ram.get('percent', 0)}%</b>", table_cell_style),
                Paragraph(f"Used: {ram.get('used_gb', 0)} GB / Total: {ram.get('total_gb', 0)} GB", table_cell_style)
            ],
            [
                Paragraph("Swap / Pagefile", table_cell_bold),
                Paragraph(f"<b>{swap.get('percent', 0)}%</b>", table_cell_style),
                Paragraph(f"Used: {swap.get('used_gb', 0)} GB / Free: {swap.get('free_gb', 0)} GB", table_cell_style)
            ],
            [
                Paragraph("Power & Battery", table_cell_bold),
                Paragraph(f"<b>{battery.get('percent', 0)}%</b>", table_cell_style),
                Paragraph(bat_str, table_cell_style)
            ]
        ]

        metrics_table = Table(metrics_data, colWidths=[120, 100, 320])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 10))

        # --- 5. Storage Volumes ---
        disks = telemetry.get("disks", [])
        if disks:
            story.append(Paragraph("Mounted Storage Drives", section_heading))
            disks_data = [[
                Paragraph("Mount", table_header_style),
                Paragraph("Type", table_header_style),
                Paragraph("Capacity (GB)", table_header_style),
                Paragraph("Used (GB)", table_header_style),
                Paragraph("Free (GB)", table_header_style),
                Paragraph("Usage %", table_header_style)
            ]]
            for d in disks:
                pct = d.get('percent', 0)
                pct_color = "#ef4444" if pct > 90 else ("#f59e0b" if pct > 80 else "#10b981")
                disks_data.append([
                    Paragraph(f"<b>{d.get('mountpoint', '')}</b>", table_cell_bold),
                    Paragraph(d.get('fstype', ''), table_cell_style),
                    Paragraph(str(d.get('total_gb', 0)), table_cell_style),
                    Paragraph(str(d.get('used_gb', 0)), table_cell_style),
                    Paragraph(str(d.get('free_gb', 0)), table_cell_style),
                    Paragraph(f"<font color='{pct_color}'><b>{pct}%</b></font>", table_cell_style),
                ])
            disks_table = Table(disks_data, colWidths=[90, 70, 95, 95, 95, 95])
            disks_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(disks_table)
            story.append(Spacer(1, 10))

        # --- 6. Top Active Processes ("Hog Hunter" Snapshot) ---
        if top_procs:
            story.append(KeepTogether([
                Paragraph("Top Resource Consumers (Hog Hunter Snapshot)", section_heading),
                Paragraph("Active processes sorted by real-time compute and memory footprints:", subtitle_style),
                Spacer(1, 4)
            ]))

            proc_data = [[
                Paragraph("PID", table_header_style),
                Paragraph("Process Name", table_header_style),
                Paragraph("CPU %", table_header_style),
                Paragraph("Memory (MB)", table_header_style),
                Paragraph("Status", table_header_style),
                Paragraph("User", table_header_style)
            ]]

            for p in top_procs[:12]:
                cpu_val = p.get('cpu_percent', 0)
                cpu_color = "#ef4444" if cpu_val > 20 else "#0f172a"
                proc_data.append([
                    Paragraph(str(p.get('pid', '')), table_cell_style),
                    Paragraph(p.get('name', '')[:25], table_cell_bold),
                    Paragraph(f"<font color='{cpu_color}'><b>{cpu_val}%</b></font>", table_cell_style),
                    Paragraph(f"{p.get('memory_mb', 0):,.1f} MB", table_cell_style),
                    Paragraph(p.get('status', 'running'), table_cell_style),
                    Paragraph(p.get('username', 'N/A').split('\\')[-1], table_cell_style)
                ])

            proc_table = Table(proc_data, colWidths=[50, 180, 65, 85, 75, 85])
            proc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('TOPPADDING', (0, 0), (-1, -1), 3.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ]))
            story.append(proc_table)
            story.append(Spacer(1, 14))

        # --- 7. Footer Notice ---
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), spaceAfter=6))
        story.append(Paragraph(
            "Report generated autonomously by <b>SysPulse v1.0</b> • Lightweight System Telemetry & Diagnostics Station",
            ParagraphStyle('Footer', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, textColor=colors.HexColor('#94a3b8'), alignment=1)
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer
