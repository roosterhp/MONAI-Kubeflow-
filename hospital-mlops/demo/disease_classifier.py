"""
Disease Classifier - Rule-based Clinical Algorithm

Phân loại bệnh dựa trên features extracted từ CT scan

Diseases detected:
1. Emphysema (Khí phổi thũng)
2. Ground-glass Opacity - GGO (Mờ kính mờ)
3. Consolidation (Đông đặc phổi - Viêm phổi)
4. Hyperinflation (Phồng phổi quá mức)
5. Restrictive Pattern (Hạn chế giãn nở)

Usage:
    from disease_classifier import DiseaseClassifier

    classifier = DiseaseClassifier()
    diagnosis = classifier.classify(features)
"""

from typing import Dict, List
import json


class DiseaseClassifier:
    """
    Rule-based disease classifier

    Sử dụng clinical decision rules để phân loại bệnh
    """

    def __init__(self, sensitivity: str = "balanced"):
        """
        Initialize classifier

        Args:
            sensitivity: "high" (more false positives, catch more diseases)
                        "balanced" (default)
                        "low" (fewer false positives, more conservative)
        """
        self.sensitivity = sensitivity
        self.rules = self._define_rules()

    def _define_rules(self) -> Dict:
        """
        Define clinical decision rules

        Thresholds based on clinical literature and radiological guidelines
        """
        # Adjust thresholds based on sensitivity
        sensitivity_multipliers = {
            "high": 0.7,      # Lower thresholds → more sensitive
            "balanced": 1.0,  # Default thresholds
            "low": 1.3        # Higher thresholds → more specific
        }

        mult = sensitivity_multipliers.get(self.sensitivity, 1.0)

        rules = {
            'emphysema': {
                'name': 'Emphysema (Khí phổi thũng)',
                'name_en': 'Emphysema',
                'condition': lambda f: f['emphysema_ratio'] > (0.15 * mult),
                'severity': lambda f: (
                    'Severe' if f['emphysema_ratio'] > 0.40 else
                    'Moderate' if f['emphysema_ratio'] > 0.25 else
                    'Mild'
                ),
                'description': lambda f: (
                    f"Air trapping detected: {f['emphysema_percentage']:.1f}% of lung volume "
                    f"has HU < -950 (emphysematous changes)"
                )
            },

            'ground_glass_opacity': {
                'name': 'Ground-Glass Opacity (Mờ kính)',
                'name_en': 'Ground-Glass Opacity',
                'condition': lambda f: f['ggo_ratio'] > (0.08 * mult),
                'severity': lambda f: (
                    'Severe' if f['ggo_ratio'] > 0.30 else
                    'Moderate' if f['ggo_ratio'] > 0.15 else
                    'Mild'
                ),
                'description': lambda f: (
                    f"Ground-glass opacity: {f['ggo_percentage']:.1f}% of lung volume "
                    f"shows hazy increased attenuation (-700 to -500 HU). "
                    f"May indicate viral pneumonia, early ILD, or edema."
                )
            },

            'consolidation': {
                'name': 'Consolidation (Đông đặc phổi)',
                'name_en': 'Consolidation',
                'condition': lambda f: f['consolidation_ratio'] > (0.03 * mult),
                'severity': lambda f: (
                    'Severe' if f['consolidation_ratio'] > 0.15 else
                    'Moderate' if f['consolidation_ratio'] > 0.08 else
                    'Mild'
                ),
                'description': lambda f: (
                    f"Consolidation: {f['consolidation_percentage']:.1f}% of lung volume "
                    f"shows high attenuation (> -300 HU). "
                    f"Suggests bacterial pneumonia, atelectasis, or fluid."
                )
            },

            'hyperinflation': {
                'name': 'Hyperinflation (Phồng phổi)',
                'name_en': 'Hyperinflation',
                'condition': lambda f: f['lung_volume_ml'] > (7000 / mult),
                'severity': lambda f: (
                    'Severe' if f['lung_volume_ml'] > 8500 else
                    'Moderate' if f['lung_volume_ml'] > 7500 else
                    'Mild'
                ),
                'description': lambda f: (
                    f"Lung hyperinflation: Total lung volume {f['lung_volume_ml']:.0f} ml "
                    f"(normal: 4000-6000 ml). Suggests air trapping or COPD."
                )
            },

            'restrictive_pattern': {
                'name': 'Restrictive Pattern (Hạn chế giãn nở)',
                'name_en': 'Restrictive Pattern',
                'condition': lambda f: f['lung_volume_ml'] < (3500 * mult),
                'severity': lambda f: (
                    'Severe' if f['lung_volume_ml'] < 2500 else
                    'Moderate' if f['lung_volume_ml'] < 3000 else
                    'Mild'
                ),
                'description': lambda f: (
                    f"Reduced lung volume: {f['lung_volume_ml']:.0f} ml "
                    f"(normal: 4000-6000 ml). May indicate fibrosis, obesity, "
                    f"or chest wall restriction."
                )
            },

            'asymmetric_disease': {
                'name': 'Asymmetric Lung Disease (Bệnh lý bất đối xứng)',
                'name_en': 'Asymmetric Disease',
                'condition': lambda f: (
                    abs(f.get('right_lung_ggo_ratio', 0) - f.get('left_lung_ggo_ratio', 0)) > 0.15
                    or abs(f.get('right_lung_consolidation_ratio', 0) - f.get('left_lung_consolidation_ratio', 0)) > 0.10
                ),
                'severity': lambda f: (
                    'Moderate' if abs(f.get('right_lung_ggo_ratio', 0) - f.get('left_lung_ggo_ratio', 0)) > 0.25 else
                    'Mild'
                ),
                'description': lambda f: (
                    f"Asymmetric disease pattern detected. "
                    f"Right lung GGO: {f.get('right_lung_ggo_ratio', 0)*100:.1f}%, "
                    f"Left lung GGO: {f.get('left_lung_ggo_ratio', 0)*100:.1f}%. "
                    f"Consider unilateral pathology."
                )
            }
        }

        return rules

    def classify(self, features: Dict) -> Dict:
        """
        Classify disease based on extracted features

        Args:
            features: dict from LungFeatureExtractor

        Returns:
            dict: {
                'is_normal': bool,
                'findings': list of detected abnormalities,
                'severity_score': float (0-10),
                'recommendations': list of clinical recommendations,
                'features_summary': dict of key features
            }
        """
        findings = []

        # Check each rule
        for disease_key, rule in self.rules.items():
            try:
                if rule['condition'](features):
                    severity = rule['severity'](features)
                    description = rule['description'](features)

                    findings.append({
                        'disease': rule['name'],
                        'disease_en': rule['name_en'],
                        'disease_key': disease_key,
                        'severity': severity,
                        'description': description,
                        'confidence': self._compute_confidence(features, disease_key)
                    })
            except Exception as e:
                # Skip if feature missing
                print(f"[WARNING] Could not evaluate rule {disease_key}: {e}")
                continue

        # Overall assessment
        is_normal = len(findings) == 0

        # Compute severity score (0-10)
        severity_score = self._compute_severity_score(findings)

        # Generate recommendations
        recommendations = self._generate_recommendations(findings, features)

        # Feature summary
        features_summary = self._summarize_features(features)

        return {
            'is_normal': is_normal,
            'status': 'NORMAL' if is_normal else 'ABNORMAL',
            'findings': findings,
            'num_findings': len(findings),
            'severity_score': severity_score,
            'severity_level': self._severity_score_to_level(severity_score),
            'recommendations': recommendations,
            'features_summary': features_summary
        }

    def _compute_confidence(self, features: Dict, disease_key: str) -> str:
        """
        Compute confidence level for a finding

        Based on how far the feature value is from the threshold
        """
        # Simple heuristic: if far above threshold → high confidence
        # If just above threshold → moderate confidence

        if disease_key == 'emphysema':
            ratio = features['emphysema_ratio']
            if ratio > 0.30:
                return 'High'
            elif ratio > 0.20:
                return 'Moderate'
            else:
                return 'Low'

        elif disease_key == 'ground_glass_opacity':
            ratio = features['ggo_ratio']
            if ratio > 0.20:
                return 'High'
            elif ratio > 0.12:
                return 'Moderate'
            else:
                return 'Low'

        elif disease_key == 'consolidation':
            ratio = features['consolidation_ratio']
            if ratio > 0.10:
                return 'High'
            elif ratio > 0.05:
                return 'Moderate'
            else:
                return 'Low'

        else:
            return 'Moderate'

    def _compute_severity_score(self, findings: List[Dict]) -> float:
        """
        Compute overall severity (0-10 scale)

        0-3: Mild
        4-6: Moderate
        7-10: Severe
        """
        if len(findings) == 0:
            return 0.0

        severity_map = {
            'Mild': 2.5,
            'Moderate': 5.0,
            'Severe': 8.5
        }

        # Average severity
        scores = [severity_map.get(f['severity'], 5.0) for f in findings]
        avg_score = sum(scores) / len(scores)

        # Penalty for multiple findings
        if len(findings) >= 3:
            avg_score = min(10.0, avg_score * 1.2)
        elif len(findings) >= 2:
            avg_score = min(10.0, avg_score * 1.1)

        return round(avg_score, 1)

    def _severity_score_to_level(self, score: float) -> str:
        """Convert severity score to level"""
        if score >= 7.0:
            return 'Severe'
        elif score >= 4.0:
            return 'Moderate'
        elif score >= 1.0:
            return 'Mild'
        else:
            return 'Normal'

    def _generate_recommendations(self, findings: List[Dict], features: Dict) -> List[str]:
        """
        Generate clinical recommendations based on findings
        """
        if len(findings) == 0:
            return [
                "No significant abnormalities detected",
                "Routine follow-up as clinically indicated"
            ]

        recommendations = []
        diseases = [f['disease_key'] for f in findings]

        # Specific recommendations
        if 'ground_glass_opacity' in diseases:
            recommendations.append(
                "Ground-glass opacity detected → Consider viral pneumonia (COVID-19, influenza), "
                "early interstitial lung disease, or pulmonary edema"
            )
            recommendations.append(
                "Clinical correlation: Check symptoms (fever, cough), lab tests (WBC, CRP), "
                "and consider RT-PCR for viral pathogens"
            )

        if 'consolidation' in diseases:
            recommendations.append(
                "Consolidation detected → Suggests bacterial pneumonia, atelectasis, or aspiration"
            )
            recommendations.append(
                "Consider antibiotic therapy if clinically indicated and follow-up imaging in 4-6 weeks"
            )

        if 'emphysema' in diseases:
            recommendations.append(
                "Emphysema pattern detected → Consistent with COPD"
            )
            recommendations.append(
                "Recommend pulmonary function tests (spirometry) and smoking cessation counseling if applicable"
            )

        if 'hyperinflation' in diseases:
            recommendations.append(
                "Lung hyperinflation → Assess for obstructive lung disease (COPD, asthma)"
            )

        if 'restrictive_pattern' in diseases:
            recommendations.append(
                "Reduced lung volume → Consider restrictive lung disease, "
                "fibrosis, or extrapulmonary restriction (obesity, chest wall)"
            )

        if 'asymmetric_disease' in diseases:
            recommendations.append(
                "Asymmetric disease pattern → Consider unilateral pathology "
                "(pneumonia, mass, pulmonary embolism)"
            )

        # General recommendations
        if len(findings) >= 2:
            recommendations.append(
                "Multiple abnormalities detected → Recommend multidisciplinary evaluation"
            )

        recommendations.append(
            "⚠️ AI-assisted analysis - Final diagnosis requires radiologist interpretation"
        )

        recommendations.append(
            "Follow-up imaging recommended in 3-6 months to assess progression"
        )

        return recommendations

    def _summarize_features(self, features: Dict) -> Dict:
        """
        Create human-readable feature summary
        """
        return {
            'Lung Volume': f"{features.get('lung_volume_ml', 0):.0f} ml",
            'Right Lung': f"{features.get('right_lung_volume_ml', 0):.0f} ml",
            'Left Lung': f"{features.get('left_lung_volume_ml', 0):.0f} ml",
            'Mean HU': f"{features.get('hu_mean', 0):.1f}",
            'HU Range': f"{features.get('hu_min', 0):.0f} to {features.get('hu_max', 0):.0f}",
            'Emphysema': f"{features.get('emphysema_percentage', 0):.1f}%",
            'Ground-Glass': f"{features.get('ggo_percentage', 0):.1f}%",
            'Consolidation': f"{features.get('consolidation_percentage', 0):.1f}%",
            'Normal Lung': f"{features.get('normal_lung_percentage', 0):.1f}%"
        }

    def generate_report(self, diagnosis: Dict) -> str:
        """
        Generate text report

        Args:
            diagnosis: Output from classify()

        Returns:
            str: Formatted clinical report
        """
        report = []
        report.append("="*60)
        report.append("AUTOMATED LUNG CT ANALYSIS REPORT")
        report.append("="*60)
        report.append("")

        # Status
        report.append(f"STATUS: {diagnosis['status']}")
        report.append(f"SEVERITY: {diagnosis['severity_level']} ({diagnosis['severity_score']}/10)")
        report.append("")

        # Findings
        if diagnosis['is_normal']:
            report.append("FINDINGS:")
            report.append("  No significant abnormalities detected")
        else:
            report.append(f"FINDINGS: ({diagnosis['num_findings']} abnormalities detected)")
            for i, finding in enumerate(diagnosis['findings'], 1):
                report.append(f"\n{i}. {finding['disease']}")
                report.append(f"   Severity: {finding['severity']}")
                report.append(f"   Confidence: {finding['confidence']}")
                report.append(f"   {finding['description']}")

        report.append("")

        # Features
        report.append("KEY MEASUREMENTS:")
        for key, value in diagnosis['features_summary'].items():
            report.append(f"  {key}: {value}")

        report.append("")

        # Recommendations
        report.append("RECOMMENDATIONS:")
        for i, rec in enumerate(diagnosis['recommendations'], 1):
            report.append(f"  {i}. {rec}")

        report.append("")
        report.append("="*60)

        return "\n".join(report)


# Example usage
if __name__ == "__main__":
    """
    Test disease classifier
    """
    print("\n" + "="*60)
    print("Testing DiseaseClassifier")
    print("="*60)

    # Create synthetic features (simulating a diseased lung)
    print("\n[INFO] Creating synthetic test features (COVID-19 patient)...")

    features = {
        'lung_volume_ml': 4200,
        'right_lung_volume_ml': 2100,
        'left_lung_volume_ml': 2100,
        'lung_volume_ratio': 1.0,
        'hu_mean': -790,
        'hu_std': 180,
        'hu_min': -980,
        'hu_max': -100,
        'emphysema_ratio': 0.08,
        'emphysema_percentage': 8.0,
        'normal_lung_ratio': 0.45,
        'normal_lung_percentage': 45.0,
        'ggo_ratio': 0.25,  # 25% GGO - significant!
        'ggo_percentage': 25.0,
        'consolidation_ratio': 0.08,  # 8% consolidation
        'consolidation_percentage': 8.0,
        'right_lung_ggo_ratio': 0.22,
        'left_lung_ggo_ratio': 0.28,
        'right_lung_consolidation_ratio': 0.06,
        'left_lung_consolidation_ratio': 0.10,
    }

    # Classify
    print("\n[INFO] Running disease classification...")
    classifier = DiseaseClassifier(sensitivity="balanced")
    diagnosis = classifier.classify(features)

    # Print report
    print("\n" + diagnosis['status'])
    print(classifier.generate_report(diagnosis))

    print("\n" + "="*60)
    print("[OK] Test completed!")
    print("="*60)
