import subprocess
import sys

def run_script(script_name):
    print(f"\n>>> RUNNING: {script_name}")
    try:
        subprocess.run(["python3", script_name], check=True)
        print(f"✅ PASSED: {script_name}")
    except subprocess.CalledProcessError:
        print(f"❌ FAILED: {script_name}")
        sys.exit(1)

def main():
    print("=== MASTER VERIFICATION SUITE ===")
    
    # 1. Compile Check (Syntax)
    print("\n>>> Checking Syntax...")
    try:
        subprocess.run(["python3", "-m", "compileall", "-q", "services/course-lifecycle/app"], check=True)
        print("✅ PASSED: Syntax Check")
    except subprocess.CalledProcessError:
        print("❌ FAILED: Syntax Check")
        sys.exit(1)

    # 2. Functional Flows
    run_script("scripts/verify_client_demo_flow.py")
    run_script("scripts/verify_graph_merge_preserves_edits.py")
    
    print("\n🎉 ALL SYSTEMS GO -- READY FOR DEMO 🎉")

if __name__ == "__main__":
    main()
