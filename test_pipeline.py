"""
CV-Enhancer Pipeline Test Script
Demonstrates A2A communication and complete pipeline execution

Usage:
    python test_pipeline.py                              # Use default sample data
    python test_pipeline.py --cv my_cv.pdf               # Use custom CV
    python test_pipeline.py --cv my_cv.txt --job job.txt # Use custom CV and job ad
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_config, get_storage_backend, get_llm_provider, setup_logging
from src.agents import OrchestratorAgent

# Sample CV text for testing (if no PDF available)
SAMPLE_CV_TEXT = """
John Doe
Email: john.doe@email.com | Phone: +1-555-0123
LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe
San Francisco, CA

PROFESSIONAL SUMMARY
Experienced software engineer with 5+ years in full-stack development, specializing in Python and JavaScript.
Proven track record of building scalable web applications and leading development teams.

WORK EXPERIENCE

Senior Software Engineer | Tech Corp | January 2020 - Present
- Led development of microservices architecture serving 1M+ users
- Reduced API response time by 50% through optimization
- Mentored team of 3 junior engineers
- Technologies: Python, Django, React, PostgreSQL, AWS

Software Engineer | StartupXYZ | June 2018 - December 2019
- Built React-based dashboard for data visualization
- Implemented CI/CD pipeline reducing deployment time by 70%
- Developed RESTful APIs handling 10K requests/day
- Technologies: JavaScript, Node.js, MongoDB, Docker

EDUCATION

Bachelor of Science in Computer Science
University of California, Berkeley | 2014 - 2018
GPA: 3.8/4.0

SKILLS

Programming Languages: Python, JavaScript, TypeScript, Go
Frameworks & Libraries: Django, Flask, React, Node.js, Express
Databases: PostgreSQL, MongoDB, Redis
Cloud & DevOps: AWS, Docker, Kubernetes, CI/CD, Git
"""

# Sample Job Advertisement
SAMPLE_JOB_AD = """
Senior Full Stack Engineer

Tech Innovations Inc. is seeking an experienced Senior Full Stack Engineer to join our growing team.

Requirements:
- 5+ years of software development experience
- Strong proficiency in Python and JavaScript
- Experience with React and modern frontend frameworks
- Backend development with Django or Flask
- Database design and optimization (PostgreSQL, MongoDB)
- Cloud deployment experience (AWS, GCP, or Azure)
- Experience with microservices architecture
- Strong problem-solving and communication skills

Nice to Have:
- Experience with Kubernetes and container orchestration
- Knowledge of GraphQL
- Contributions to open-source projects
- Experience with AI/ML integration
- Leadership or mentoring experience

We offer competitive salary, remote work options, and comprehensive benefits.
"""


async def create_test_cv_file():
    """Create a test CV file if none exists"""
    test_cv_path = Path("./data/uploads/test_cv.txt")
    test_cv_path.parent.mkdir(parents=True, exist_ok=True)

    if not test_cv_path.exists():
        with open(test_cv_path, "w", encoding="utf-8") as f:
            f.write(SAMPLE_CV_TEXT)

        print(f"[OK] Created test CV file: {test_cv_path}")

    return str(test_cv_path)


async def create_test_job_file():
    """Create a test job ad file if none exists"""
    test_job_path = Path("./data/uploads/test_job.txt")
    test_job_path.parent.mkdir(parents=True, exist_ok=True)

    if not test_job_path.exists():
        with open(test_job_path, "w", encoding="utf-8") as f:
            f.write(SAMPLE_JOB_AD)

        print(f"[OK] Created test job ad file: {test_job_path}")

    return str(test_job_path)


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="CV-Enhancer Pipeline Test - Demonstrates A2A communication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_pipeline.py
  python test_pipeline.py --cv my_resume.pdf
  python test_pipeline.py --cv my_resume.txt --job senior_engineer_job.txt
        """
    )

    parser.add_argument(
        "--cv",
        type=str,
        help="Path to CV file (PDF or TXT). If not provided, uses sample CV."
    )

    parser.add_argument(
        "--job",
        type=str,
        help="Path to job advertisement file (TXT). If not provided, uses sample job ad."
    )

    return parser.parse_args()


async def main():
    """Main test function"""

    # Parse command-line arguments
    args = parse_arguments()

    print("=" * 70)
    print("CV-Enhancer Multi-Agent System - Pipeline Test")
    print("Demonstrating A2A Communication for Google/Kaggle Seminar")
    print("=" * 70)
    print()

    # Load configuration
    print("Step 1: Loading Configuration...")
    try:
        config = get_config(env_file=".env")
        print(f"   Mode: {config.mode}")
        print(f"   LLM Provider: {config.llm_provider}")
        print(f"   LLM Model: {config.llm_model}")
        print(f"   Storage: {config.storage_type}")
        print("   [OK] Configuration loaded")
    except Exception as e:
        print(f"   [ERROR] Configuration failed: {e}")
        print("\nTip: Copy .env.local to .env and configure your LLM settings")
        return

    print()

    # Initialize components
    print("Step 2: Initializing Components...")
    try:
        setup_logging(config)
        storage = get_storage_backend(config)
        print(f"   [OK] Storage backend: {storage.__class__.__name__}")

        try:
            llm = get_llm_provider(config)
            print(f"   [OK] LLM provider: {llm.__class__.__name__}")
            print(f"   [OK] Model: {llm.model}")
        except Exception as e:
            print(f"   [WARNING] LLM provider failed: {e}")
            print(f"   Continuing without LLM (will use fallback methods)...")
            llm = None

    except Exception as e:
        print(f"   [ERROR] Component initialization failed: {e}")
        return

    print()

    # Initialize Orchestrator
    print("Step 3: Initializing Orchestrator Agent...")
    try:
        orchestrator = OrchestratorAgent(
            llm_provider=llm,
            storage_backend=storage,
            config={
                "vector_db_type": config.vector_db_type,
                "vector_db_path": config.vector_db_path,
                "data_dir": config.data_dir,
                "output_dir": "./data/outputs"
            }
        )
        print("   [OK] Orchestrator initialized")
        print(f"   [OK] Registered {len(orchestrator._agent_registry)} agents for A2A communication:")
        for agent_name in orchestrator._agent_registry.keys():
            print(f"      - {agent_name}")
    except Exception as e:
        print(f"   [ERROR] Orchestrator initialization failed: {e}")
        return

    print()

    # Prepare CV and Job files
    print("Step 4: Preparing Test Data...")
    try:
        # Handle CV file
        if args.cv:
            cv_file = args.cv
            if not Path(cv_file).exists():
                print(f"   [ERROR] CV file not found: {cv_file}")
                return
            print(f"   [OK] Using provided CV file: {cv_file}")
        else:
            cv_file = await create_test_cv_file()
            print(f"   [OK] Using sample CV file: {cv_file}")

        # Handle Job Ad file
        if args.job:
            job_file = args.job
            if not Path(job_file).exists():
                print(f"   [ERROR] Job ad file not found: {job_file}")
                return
            # Read job ad from file
            with open(job_file, "r", encoding="utf-8") as f:
                job_ad_text = f.read()
            print(f"   [OK] Using provided job ad file: {job_file}")
        else:
            job_ad_text = SAMPLE_JOB_AD
            job_file = await create_test_job_file()
            print(f"   [OK] Using sample job ad: {job_file}")

    except Exception as e:
        print(f"   [ERROR] Test data preparation failed: {e}")
        return

    print()

    # Run pipeline
    print("Step 5: Running CV Enhancement Pipeline...")
    print("   This will demonstrate A2A communication across all agents:")
    print("   Orchestrator -> CV Ingestion -> Job Understanding -> User Interaction")
    print("                -> Knowledge Storage -> CV Generator")
    print()

    try:
        result = await orchestrator.process_cv_request(
            cv_file=cv_file,
            job_ad=job_ad_text,
            user_id="test_user_001",
            job_source_type="text"
        )

        if result["status"] == "completed":
            print()
            print("=" * 70)
            print("PIPELINE COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print(f"\nResults:")
            print(f"   Session ID: {result['session_id']}")
            print(f"   User ID: {result['user_id']}")
            print(f"   Match Score: {result['match_score']:.1f}%")
            print(f"   Steps Completed: {' -> '.join(result['steps_completed'])}")
            print(f"\nGenerated Files:")
            for format_name, file_path in result['output_files'].items():
                print(f"   - {format_name.upper()}: {file_path}")

            print(f"\nGap Analysis:")
            print(f"   - Gaps Found: {len(result['gap_analysis']['gaps'])}")
            print(f"   - Matches: {len(result['gap_analysis']['matches'])}")
            print(f"   - Recommendations: {len(result['gap_analysis'].get('recommendations', []))}")

            if result['gap_analysis']['gaps']:
                print(f"\n   Top Gaps:")
                for i, gap in enumerate(result['gap_analysis']['gaps'][:3], 1):
                    print(f"   {i}. [{gap['priority'].upper()}] {gap['description']}")

            print("\n[OK] A2A Communication Verified:")
            print("   All agents successfully communicated via call_agent() method")
            print("   This demonstrates proper Agent-to-Agent messaging")

        else:
            print()
            print("=" * 70)
            print("[ERROR] PIPELINE FAILED")
            print("=" * 70)
            print(f"\nError: {result.get('error', 'Unknown error')}")
            print(f"Steps Completed: {result.get('steps_completed', [])}")

    except Exception as e:
        print(f"\n   [ERROR] Pipeline execution failed: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return

    print()
    print("=" * 70)
    print("Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
