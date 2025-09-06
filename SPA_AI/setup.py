#!/usr/bin/env python3
"""
SPA VIP Setup Script
Automated setup for the entire SPA VIP system
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, description):
    """Run a command and handle errors"""
    logger.info(f"{description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"{description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"{description} - Failed: {e.stderr}")
        return False

def setup_spa_vip():
    """Setup entire SPA VIP system"""
    
    logger.info("STARTING SPA VIP SYSTEM SETUP")
    logger.info("="*60)
    
    # Create necessary directories
    logger.info("Creating directories...")
    os.makedirs('logs', exist_ok=True)
    logger.info("Logs directory created")
    
    # Install database dependencies
    if not run_command("pip install -r database/requirements.txt", 
                      "Installing database dependencies"):
        return False
    
    # Install crawl dependencies
    if not run_command("pip install -r crawl/requirements.txt", 
                      "Installing crawl dependencies"):
        return False
    
    # Install summarization dependencies  
    if not run_command("pip install -r summarization/requirements.txt", 
                      "Installing summarization dependencies"):
        return False
    
    # Test database connection
    logger.info("Testing database connection...")
    if not run_command("python database/test_connection.py", 
                      "Testing database connection"):
        logger.warning("Database connection test failed - please check configuration")
    
    # Test main.py controller
    logger.info("Testing main controller...")
    if not run_command("python main.py --status", 
                      "Testing main controller"):
        logger.warning("Main controller test failed")
    
    logger.info("\n" + "="*60)
    logger.info("SPA VIP SETUP COMPLETED!")
    logger.info("="*60)
    
    # Next steps instructions
    logger.info("NEXT STEPS:")
    logger.info("1. Verify model files in model_AI/summarization_model/model_vit5/")
    logger.info("2. Run: python main.py --status")
    logger.info("3. Run: python main.py --full")
    logger.info("")
    logger.info("Quick commands:")
    logger.info("  python main.py --help          # Show all options")
    logger.info("  python main.py --status        # Check system status")
    logger.info("  python main.py --full          # Run complete pipeline")
    logger.info("="*60)
    
    return True

if __name__ == "__main__":
    success = setup_spa_vip()
    sys.exit(0 if success else 1)
