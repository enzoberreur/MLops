"""
Launch the Streamlit WebApp.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run the Streamlit app."""
    app_path = Path(__file__).parent / "src" / "webapp" / "app.py"
    
    print("🌿 Starting Plant Classification WebApp...")
    print(f"📂 App location: {app_path}")
    print("🌐 Opening in browser...")
    print("\n" + "="*70)
    print("WebApp will be available at: http://localhost:8501")
    print("API should be running at: http://localhost:8000")
    print("="*70 + "\n")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(app_path),
            "--server.port=8501",
            "--server.address=localhost",
            "--browser.gatherUsageStats=false"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 WebApp stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting WebApp: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
