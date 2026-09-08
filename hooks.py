"""Install transport dependencies into the framework runtime."""
import subprocess
import sys


def install(**kwargs):
    subprocess.run([sys.executable, "-m", "pip", "install", 'requests==2.34.2', 'defusedxml==0.7.1'], check=True)
