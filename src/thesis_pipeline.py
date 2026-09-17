"""Rebuild the three retained thesis analyses from prepared local inputs.

Source preparation is documented in docs/pipeline.md. Legacy supporting models
and alternative rate allocations are intentionally outside this entry point.
"""
import subprocess
import sys

MODULES = [
    'src.tables.pipeline', 'src.tables.exact_data',
    'src.tables.counter_selection_audit',
    'src.analysis.oe_analysis', 'src.tables.traffic_corrected_oe',
    'src.tables.monthly_vkt_rate', 'src.tables.monthly_vkt_discrepancy',
    'src.tables.annual_coverage', 'src.tables.conditions',
    'src.tables.revision', 'src.tables.joint_detail', 'src.tables.thesis', 'src.tables.thesis_alignment', 'src.tables.results_context',
    'src.figures.annual_coverage', 'src.figures.conditions',
    'src.figures.accident_map', 'src.figures.oe_histo',
    'src.figures.traffic_weather_response', 'src.figures.traffic_corrected_oe',
    'src.figures.monthly_vkt_rate', 'src.figures.joint_detail',
]


def main():
    for module in MODULES:
        print(f'Running {module}', flush=True)
        subprocess.run([sys.executable, '-m', module], check=True)


if __name__ == '__main__':
    main()
