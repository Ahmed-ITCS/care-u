import io
import logging
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def generate_lab_report(lab_request, user):
    from apps.laboratory.models import LabReport

    try:
        from weasyprint import HTML
        html_content = f"""
        <html><body>
        <h1>CARE-U - Lab Report</h1>
        <p>Request: {lab_request.request_number}</p>
        <p>Patient: {lab_request.patient.full_name} ({lab_request.patient.mr_number})</p>
        <table border="1" cellpadding="5">
        <tr><th>Test</th><th>Result</th><th>Unit</th><th>Reference</th></tr>
        """
        for item in lab_request.items.all():
            result = getattr(item, 'result', None)
            if result:
                html_content += f"""
                <tr>
                    <td>{item.test.name}</td>
                    <td>{result.result_value}</td>
                    <td>{result.unit}</td>
                    <td>{result.reference_range}</td>
                </tr>
                """
        html_content += "</table></body></html>"

        pdf = HTML(string=html_content).write_pdf()
        report, _ = LabReport.objects.get_or_create(request=lab_request)
        report.pdf_file.save(
            f'{lab_request.request_number}.pdf',
            ContentFile(pdf),
            save=False,
        )
        report.generated_by = user
        report.is_final = True
        report.save()

        from apps.notifications.services import notify_user
        if lab_request.patient.user_account:
            notify_user(
                lab_request.patient.user_account,
                'Lab Results Ready',
                f'Your lab results for {lab_request.request_number} are ready.',
                'lab_result',
            )
        return report
    except Exception as e:
        logger.error(f'Failed to generate lab report: {e}')
        return None
