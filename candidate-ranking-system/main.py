"""
CLI Entry Point
Run the ranking pipeline from the command line.
Usage: python main.py [--jd path] [--candidates path] [--output path] [--no-embeddings]
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import setup_logger
from src.utils.file_utils import Config
from src.pipeline.pipeline_manager import PipelineManager


def main():
    parser = argparse.ArgumentParser(
        description="Adaptive Multi-Stage Candidate Intelligence Engine"
    )
    parser.add_argument("--jd", type=str, default=None,
                        help="Path to job description DOCX file")
    parser.add_argument("--candidates", type=str, default=None,
                        help="Path to candidates JSONL/JSON file")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory")
    parser.add_argument("--out", type=str, default=None,
                        help="Path to save the final submission CSV directly")
    parser.add_argument("--no-embeddings", action="store_true",
                        help="Disable semantic embeddings (faster, less accurate)")
    parser.add_argument("--top-k", type=int, default=100,
                        help="Number of top candidates to rank")

    args = parser.parse_args()

    # Setup logging
    setup_logger(level="INFO")

    # Load config
    config = Config.load()

    # Create and run pipeline
    pipeline = PipelineManager(config=config)

    if args.top_k:
        pipeline.top_k = args.top_k

    print("=" * 60)
    print("  Adaptive Multi-Stage Candidate Intelligence Engine")
    print("=" * 60)
    print()

    try:
        # Resolve relative paths to absolute so they work regardless of CWD
        jd_path = str(Path(args.jd).resolve()) if args.jd else None
        candidates_path = str(Path(args.candidates).resolve()) if args.candidates else None
        output_dir = str(Path(args.output).resolve()) if args.output else None
        output_csv = str(Path(args.out).resolve()) if args.out else None

        results = pipeline.run(
            jd_path=jd_path,
            candidates_path=candidates_path,
            output_dir=output_dir,
            use_embeddings=not args.no_embeddings,
            output_csv=output_csv,
        )

        print(f"\n{'=' * 60}")
        print(f"  Pipeline Complete!")
        print(f"  Total candidates: {pipeline.metrics['total_candidates']}")
        print(f"  After Stage 1:    {pipeline.metrics['candidates_after_stage1']}")
        print(f"  Final ranked:     {pipeline.metrics['candidates_ranked']}")
        print(f"  Runtime:          {pipeline.metrics['runtime_seconds']:.1f}s")
        print(f"{'=' * 60}")
        print(f"\nTop 10 Candidates:")
        print(f"{'Rank':<6}{'Score':<10}{'Name':<25}{'Title':<35}{'Exp(y)':<8}")
        print("-" * 84)

        for rc in results[:10]:
            print(
                f"{rc.final_rank:<6}"
                f"{rc.final_score:<10.4f}"
                f"{rc.candidate_name[:24]:<25}"
                f"{rc.current_title[:34]:<35}"
                f"{rc.years_experience:<8.1f}"
            )

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
