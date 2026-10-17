#!/usr/bin/env python3
import sys
def check():
    print("=== Environment Check ===")
    print(f"Python: {sys.version}")
    
    packages = ['torch', 'torchvision', 'sklearn', 'cv2', 'fastapi', 'numpy', 'joblib']
    for pkg in packages:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, '__version__', 'OK')
            print(f"{pkg}: {ver}")
        except ImportError:
            print(f"{pkg}: NOT FOUND")
    
    print("\n=== Ready to develop! ===")
if __name__ == "__main__":
    check()
