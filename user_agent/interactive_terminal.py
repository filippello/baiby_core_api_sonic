import os
import subprocess
import sys
from pathlib import Path
import contextlib

def main_menu():
    # Get the base path of the project
    base_path = Path(__file__).parent
    
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print("\n🤖 MultiversX Agent Terminal\n")
        print("1. Transfer tokens to another wallet")
        print("2. Swap EGLD for ASH")
        print("3. Exit")
        
        choice = input("\nSelect an option (1-3): ")
        
        if choice == "1":
            reason = input("\nEnter the reason for the wallet drain: ")
            os.environ['TRANSACTION_REASON'] = reason
            try:
                with open(os.devnull, 'w') as devnull:
                    subprocess.run([sys.executable, str(base_path / "userAgent.py")], 
                                stderr=devnull)
                print("\n✅ Wallet drain executed")
            except Exception as e:
                print(f"\n❌ Error: {e}")
            
        elif choice == "2":
            reason = input("\nEnter the reason for EGLD->ASH swap: ")
            os.environ['TRANSACTION_REASON'] = reason
            try:
                with open(os.devnull, 'w') as devnull:
                    subprocess.run([sys.executable, str(base_path / "userAgentswap.py")], 
                                stderr=devnull)
                print("\n✅ Swap executed")
            except Exception as e:
                print(f"\n❌ Error: {e}")
            
        elif choice == "3":
            print("\n👋 Goodbye!")
            break
            
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main_menu() 