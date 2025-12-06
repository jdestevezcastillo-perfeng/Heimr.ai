import xml.etree.ElementTree as ET
from datetime import datetime

class JUnitReporter:
    """
    Generates JUnit XML reports for CI/CD test dashboards.
    """
    
    def __init__(self, output_path: str = "heimr-junit.xml"):
        self.output_path = output_path
    
    def generate_report(self, stats: dict, anomalies: dict, failure_reasons: list = None, tags: dict = None):
        """
        Generate JUnit XML report.
        """
        failed = len(failure_reasons) > 0 if failure_reasons else False
        
        testsuites = ET.Element("testsuites")
        testsuite = ET.SubElement(testsuites, "testsuite", {
            "name": "Heimr Performance Analysis",
            "tests": "3",  # Baselines: Error Rate, Anomalies, Thresholds
            "failures": str(len(failure_reasons)) if failure_reasons else "0",
            "timestamp": datetime.now().isoformat(),
            "time": "0"  # We don't track analysis duration here easily
        })
        
        # Test Case 1: Error Rate
        tc_errors = ET.SubElement(testsuite, "testcase", {"name": "Error Rate Check", "classname": "Performance.ErrorRate"})
        if stats.get('error_rate', 0) > 0:
            failure = ET.SubElement(tc_errors, "failure", {"message": f"Error Rate is {stats['error_rate']:.2f}%"})
            failure.text = f"Error Rate exceeded 0%. Value: {stats['error_rate']:.2f}%"
            
        # Test Case 2: Anomalies
        tc_anomalies = ET.SubElement(testsuite, "testcase", {"name": "Anomaly Detection", "classname": "Performance.Anomalies"})
        if anomalies['count'] > 0:
            failure = ET.SubElement(tc_anomalies, "failure", {"message": f"{anomalies['count']} Latency Anomalies Detected"})
            failure.text = f"Found {anomalies['count']} anomalies. Max Latency: {anomalies['max_latency']:.2f}ms"
            
        # Test Case 3: Thresholds / Gating
        tc_gating = ET.SubElement(testsuite, "testcase", {"name": "Performance Gating", "classname": "Performance.Gating"})
        if failure_reasons:
            # Filter for non-error/non-anomaly reasons if possible, or just dump all failures here
            gating_failures = [r for r in failure_reasons if "Error Rate" not in r and "Anomalies" not in r]
            if gating_failures:
                failure = ET.SubElement(tc_gating, "failure", {"message": "Performance thresholds violated"})
                failure.text = "\n".join(gating_failures)
        
        # Properties (Context Tags)
        if tags:
            properties = ET.SubElement(testsuite, "properties")
            for k, v in tags.items():
                prop = ET.SubElement(properties, "property", {"name": k, "value": str(v)})

        tree = ET.ElementTree(testsuites)
        try:
            tree.write(self.output_path, encoding='utf-8', xml_declaration=True)
            print(f"✅ JUnit XML report saved to: {self.output_path}")
        except Exception as e:
            print(f"Warning: Failed to generate JUnit report: {e}")
