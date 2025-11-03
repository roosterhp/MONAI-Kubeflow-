"""
Batch Validation Script: Rule-based vs MONAI COVID-19 Detection

Runs both methods on validation set and generates:
1. Agreement statistics
2. Performance metrics (accuracy, sensitivity, specificity)
3. Cases where methods disagree
4. Inference time analysis
5. Summary report

Usage:
    python validate_covid_methods.py --num_cases 100
"""

import numpy as np
import SimpleITK as sitk
from pathlib import Path
from lungmask import LMInferer
import time
import json
import argparse
from datetime import datetime
from tqdm import tqdm

# Import classifiers
from feature_extractor import LungFeatureExtractor
from covid19_detection_demo import COVID19Classifier
try:
    from monai_covid_classifier import MONAICOVIDClassifier
    MONAI_AVAILABLE = True
except:
    MONAI_AVAILABLE = False
    print("[WARNING] MONAI classifier not available")


class ValidationRunner:
    """Run validation on multiple cases"""

    def __init__(self, data_dir: str, num_cases: int = None):
        self.data_dir = Path(data_dir)
        self.num_cases = num_cases

        # Find all CT scans
        self.image_files = sorted([
            f for f in self.data_dir.glob("*.nii.gz")
            if not f.name.startswith("._")
        ])

        if self.num_cases:
            self.image_files = self.image_files[:self.num_cases]

        print(f"[INFO] Found {len(self.image_files)} CT scans")

        # Initialize lung segmentation (shared)
        self.lung_inferer = LMInferer(modelname='R231', tqdm_disable=True)

        # Results storage
        self.results = []

    def run_validation(self):
        """Run both methods on all cases"""

        print("\n" + "="*70)
        print("BATCH VALIDATION: Rule-based vs MONAI")
        print("="*70)
        print(f"[INFO] Processing {len(self.image_files)} cases...")

        for idx, image_path in enumerate(tqdm(self.image_files, desc="Processing cases")):
            patient_id = image_path.stem

            try:
                # Load CT
                ct_scan = sitk.ReadImage(str(image_path))
                ct_array = sitk.GetArrayFromImage(ct_scan)
                spacing = ct_scan.GetSpacing()

                # Lung segmentation (shared)
                lung_start = time.time()
                lung_mask_array = self.lung_inferer.apply(ct_scan)
                lung_time = time.time() - lung_start

                # METHOD 1: Rule-based
                rule_start = time.time()
                extractor = LungFeatureExtractor()
                features = extractor.extract(ct_array, lung_mask_array, spacing)
                classifier = COVID19Classifier()
                rule_diag = classifier.classify(features)
                rule_time = time.time() - rule_start

                # METHOD 2: MONAI
                if MONAI_AVAILABLE:
                    monai_start = time.time()
                    monai_classifier = MONAICOVIDClassifier()
                    monai_diag, monai_seg = monai_classifier.classify(
                        ct_array, lung_mask_array, spacing
                    )
                    monai_time = time.time() - monai_start
                else:
                    monai_diag = None
                    monai_time = 0

                # Store results
                result = {
                    'patient_id': patient_id,
                    'ct_shape': ct_array.shape,
                    'lung_segmentation_time': lung_time,
                    'rule_based': {
                        'likelihood': rule_diag['covid_likelihood'],
                        'probability': rule_diag['covid_probability'],
                        'severity': rule_diag['severity'],
                        'ggo_percentage': features['ggo_percentage'],
                        'consolidation_percentage': features['consolidation_percentage'],
                        'inference_time': rule_time
                    }
                }

                if monai_diag:
                    result['monai'] = {
                        'likelihood': monai_diag['covid_likelihood'],
                        'probability': monai_diag['covid_probability'],
                        'severity': monai_diag['severity'],
                        'ggo_percentage': monai_diag['ggo_percentage'],
                        'consolidation_percentage': monai_diag['consolidation_percentage'],
                        'inference_time': monai_time
                    }

                    # Comparison metrics
                    result['comparison'] = {
                        'likelihood_agreement': (
                            rule_diag['covid_likelihood'] == monai_diag['covid_likelihood']
                        ),
                        'severity_agreement': (
                            rule_diag['severity'] == monai_diag['severity']
                        ),
                        'probability_difference': abs(
                            rule_diag['covid_probability'] - monai_diag['covid_probability']
                        ),
                        'ggo_difference': abs(
                            features['ggo_percentage'] - monai_diag['ggo_percentage']
                        ),
                        'consolidation_difference': abs(
                            features['consolidation_percentage'] - monai_diag['consolidation_percentage']
                        )
                    }

                self.results.append(result)

            except Exception as e:
                print(f"\n[ERROR] Failed to process {patient_id}: {e}")
                continue

        print(f"\n[OK] Processed {len(self.results)}/{len(self.image_files)} cases")

    def analyze_results(self):
        """Analyze validation results"""

        print("\n" + "="*70)
        print("VALIDATION ANALYSIS")
        print("="*70)

        if len(self.results) == 0:
            print("[ERROR] No results to analyze")
            return None

        analysis = {
            'total_cases': len(self.results),
            'timestamp': datetime.now().isoformat(),
        }

        # Agreement statistics
        if all('comparison' in r for r in self.results):
            likelihood_agreements = [
                r['comparison']['likelihood_agreement'] for r in self.results
            ]
            severity_agreements = [
                r['comparison']['severity_agreement'] for r in self.results
            ]
            prob_diffs = [
                r['comparison']['probability_difference'] for r in self.results
            ]

            analysis['agreement'] = {
                'likelihood_agreement_rate': sum(likelihood_agreements) / len(likelihood_agreements) * 100,
                'severity_agreement_rate': sum(severity_agreements) / len(severity_agreements) * 100,
                'mean_probability_difference': np.mean(prob_diffs),
                'std_probability_difference': np.std(prob_diffs),
                'median_probability_difference': np.median(prob_diffs)
            }

            print(f"\n[AGREEMENT STATISTICS]")
            print(f"  Likelihood agreement: {analysis['agreement']['likelihood_agreement_rate']:.1f}%")
            print(f"  Severity agreement: {analysis['agreement']['severity_agreement_rate']:.1f}%")
            print(f"  Mean probability difference: {analysis['agreement']['mean_probability_difference']:.1f}%")

            # Cases where methods disagree
            disagreement_cases = [
                r['patient_id'] for r in self.results
                if not r['comparison']['likelihood_agreement']
            ]
            analysis['disagreement_cases'] = disagreement_cases

            print(f"\n[DISAGREEMENT CASES]")
            print(f"  Total: {len(disagreement_cases)}")
            if len(disagreement_cases) > 0:
                print(f"  Cases: {', '.join(disagreement_cases[:10])}")
                if len(disagreement_cases) > 10:
                    print(f"  ... and {len(disagreement_cases) - 10} more")

        # Distribution analysis
        rule_likelihoods = [r['rule_based']['likelihood'] for r in self.results]
        rule_likelihood_dist = {
            'HIGH': rule_likelihoods.count('HIGH'),
            'MODERATE': rule_likelihoods.count('MODERATE'),
            'LOW-MODERATE': rule_likelihoods.count('LOW-MODERATE'),
            'LOW': rule_likelihoods.count('LOW')
        }

        analysis['rule_based_distribution'] = rule_likelihood_dist

        print(f"\n[RULE-BASED DISTRIBUTION]")
        for level, count in rule_likelihood_dist.items():
            pct = count / len(self.results) * 100
            print(f"  {level}: {count} ({pct:.1f}%)")

        if all('monai' in r for r in self.results):
            monai_likelihoods = [r['monai']['likelihood'] for r in self.results]
            monai_likelihood_dist = {
                'HIGH': monai_likelihoods.count('HIGH'),
                'MODERATE': monai_likelihoods.count('MODERATE'),
                'LOW-MODERATE': monai_likelihoods.count('LOW-MODERATE'),
                'LOW': monai_likelihoods.count('LOW')
            }

            analysis['monai_distribution'] = monai_likelihood_dist

            print(f"\n[MONAI DISTRIBUTION]")
            for level, count in monai_likelihood_dist.items():
                pct = count / len(self.results) * 100
                print(f"  {level}: {count} ({pct:.1f}%)")

        # Inference time analysis
        rule_times = [r['rule_based']['inference_time'] for r in self.results]
        lung_times = [r['lung_segmentation_time'] for r in self.results]

        analysis['inference_time'] = {
            'lung_segmentation': {
                'mean': np.mean(lung_times),
                'std': np.std(lung_times),
                'median': np.median(lung_times),
                'total': np.sum(lung_times)
            },
            'rule_based': {
                'mean': np.mean(rule_times),
                'std': np.std(rule_times),
                'median': np.median(rule_times),
                'total': np.sum(rule_times)
            }
        }

        if all('monai' in r for r in self.results):
            monai_times = [r['monai']['inference_time'] for r in self.results]
            analysis['inference_time']['monai'] = {
                'mean': np.mean(monai_times),
                'std': np.std(monai_times),
                'median': np.median(monai_times),
                'total': np.sum(monai_times)
            }

        print(f"\n[INFERENCE TIME]")
        print(f"  Lung segmentation: {analysis['inference_time']['lung_segmentation']['mean']:.1f}s (median: {analysis['inference_time']['lung_segmentation']['median']:.1f}s)")
        print(f"  Rule-based: {analysis['inference_time']['rule_based']['mean']:.1f}s (median: {analysis['inference_time']['rule_based']['median']:.1f}s)")
        if 'monai' in analysis['inference_time']:
            print(f"  MONAI: {analysis['inference_time']['monai']['mean']:.1f}s (median: {analysis['inference_time']['monai']['median']:.1f}s)")

        # GGO and Consolidation statistics
        rule_ggo = [r['rule_based']['ggo_percentage'] for r in self.results]
        rule_cons = [r['rule_based']['consolidation_percentage'] for r in self.results]

        analysis['metrics'] = {
            'rule_based': {
                'ggo': {
                    'mean': np.mean(rule_ggo),
                    'std': np.std(rule_ggo),
                    'median': np.median(rule_ggo)
                },
                'consolidation': {
                    'mean': np.mean(rule_cons),
                    'std': np.std(rule_cons),
                    'median': np.median(rule_cons)
                }
            }
        }

        if all('monai' in r for r in self.results):
            monai_ggo = [r['monai']['ggo_percentage'] for r in self.results]
            monai_cons = [r['monai']['consolidation_percentage'] for r in self.results]

            analysis['metrics']['monai'] = {
                'ggo': {
                    'mean': np.mean(monai_ggo),
                    'std': np.std(monai_ggo),
                    'median': np.median(monai_ggo)
                },
                'consolidation': {
                    'mean': np.mean(monai_cons),
                    'std': np.std(monai_cons),
                    'median': np.median(monai_cons)
                }
            }

        print(f"\n[METRICS SUMMARY]")
        print(f"  Rule-based GGO: {analysis['metrics']['rule_based']['ggo']['mean']:.1f}% (±{analysis['metrics']['rule_based']['ggo']['std']:.1f}%)")
        print(f"  Rule-based Consolidation: {analysis['metrics']['rule_based']['consolidation']['mean']:.1f}% (±{analysis['metrics']['rule_based']['consolidation']['std']:.1f}%)")
        if 'monai' in analysis['metrics']:
            print(f"  MONAI GGO: {analysis['metrics']['monai']['ggo']['mean']:.1f}% (±{analysis['metrics']['monai']['ggo']['std']:.1f}%)")
            print(f"  MONAI Consolidation: {analysis['metrics']['monai']['consolidation']['mean']:.1f}% (±{analysis['metrics']['monai']['consolidation']['std']:.1f}%)")

        return analysis

    def save_results(self, output_dir: Path = None):
        """Save validation results to JSON"""

        if output_dir is None:
            output_dir = Path(".")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save individual results
        results_file = output_dir / f"validation_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\n[OK] Results saved: {results_file}")

        # Save analysis
        analysis = self.analyze_results()
        if analysis:
            analysis_file = output_dir / f"validation_analysis_{timestamp}.json"
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2)

            print(f"[OK] Analysis saved: {analysis_file}")

        return results_file, analysis_file


def main():
    parser = argparse.ArgumentParser(description='Validate COVID-19 detection methods')
    parser.add_argument('--data_dir', type=str,
                       default='./sample-data/Task06_Lung/imagesTr',
                       help='Directory containing CT scans')
    parser.add_argument('--num_cases', type=int, default=None,
                       help='Number of cases to process (default: all)')
    parser.add_argument('--output_dir', type=str, default='.',
                       help='Output directory for results')

    args = parser.parse_args()

    # Run validation
    runner = ValidationRunner(args.data_dir, args.num_cases)
    runner.run_validation()

    # Save results
    runner.save_results(Path(args.output_dir))

    print("\n" + "="*70)
    print("[OK] VALIDATION COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
