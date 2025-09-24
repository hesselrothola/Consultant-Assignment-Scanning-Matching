#!/usr/bin/env python3
"""
Test CV upload functionality through the web interface.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scrapers.playwright_client import PlaywrightMCPClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_cv_upload():
    """Test the CV upload modal and functionality."""
    
    client = PlaywrightMCPClient()
    
    try:
        # Start browser
        logger.info("Starting browser...")
        await client.start()
        
        # Navigate to consultants page
        logger.info("Navigating to consultants page...")
        await client.navigate("https://n8n.cognova.net/consultant/consultants")
        
        # Wait for page to load
        await client.wait_for(time=2)
        
        # Take screenshot of initial page
        logger.info("Taking screenshot of consultants page...")
        await client.take_screenshot("consultants_page.png")
        
        # Get page snapshot
        snapshot = await client.snapshot()
        logger.info(f"Page loaded. Found {len(snapshot.get('elements', []))} elements")
        
        # Find and click Upload CV button
        upload_button = None
        for elem in snapshot.get('elements', []):
            if 'Upload CV' in elem.get('text', ''):
                upload_button = elem
                break
        
        if upload_button:
            logger.info(f"Found Upload CV button: {upload_button.get('ref')}")
            await client.click(
                element="Upload CV button",
                ref=upload_button.get('ref')
            )
            
            # Wait for modal to appear
            await client.wait_for(time=1)
            
            # Take screenshot of modal
            logger.info("Taking screenshot of upload modal...")
            await client.take_screenshot("upload_modal.png")
            
            # Get updated snapshot
            modal_snapshot = await client.snapshot()
            
            # Check if modal is visible
            modal_visible = False
            for elem in modal_snapshot.get('elements', []):
                if 'Upload Consultant CV' in elem.get('text', ''):
                    modal_visible = True
                    logger.info("✅ Upload modal opened successfully!")
                    break
            
            if not modal_visible:
                logger.error("❌ Upload modal did not open")
                
            # Find file input
            file_input = None
            for elem in modal_snapshot.get('elements', []):
                if elem.get('type') == 'file':
                    file_input = elem
                    break
                    
            if file_input:
                logger.info(f"Found file input: {file_input.get('ref')}")
                
                # Create test CV file
                test_cv_path = "/tmp/test_consultant.txt"
                with open(test_cv_path, 'w') as f:
                    f.write("""Anna Andersson
Senior Data Scientist & ML Engineer
Stockholm, Sweden
anna@example.com

15+ years experience in AI/ML
Skills: Python, TensorFlow, AWS, Kubernetes
Rate: 1,500 SEK/hour""")
                
                # Upload file
                logger.info("Uploading test CV file...")
                await client.file_upload([test_cv_path])
                
                # Wait for processing
                await client.wait_for(time=3)
                
                # Take final screenshot
                await client.take_screenshot("upload_result.png")
                logger.info("✅ CV upload test completed!")
            else:
                logger.error("❌ Could not find file input element")
                
        else:
            logger.error("❌ Upload CV button not found on page")
            
            # Log available buttons for debugging
            buttons = [elem.get('text', '') for elem in snapshot.get('elements', []) 
                      if elem.get('tag') == 'button']
            logger.info(f"Available buttons: {buttons}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close browser
        await client.close()
        logger.info("Browser closed")


if __name__ == "__main__":
    asyncio.run(test_cv_upload())