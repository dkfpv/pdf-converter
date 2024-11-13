import requests
import logging
import os
from pathlib import Path
import fitz
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PDFConverterTester:
    def __init__(self):
        self.api_url = "https://pdf-converter-production-f9b0.up.railway.app"
        self.test_pdf_path = "/Users/danilakilin/Downloads/Etiquette (6).pdf"
        self.local_storage = Path("test_storage")

    def setup_local_storage(self):
        """Test storage setup locally"""
        try:
            logger.info("Setting up local test storage")
            
            # Create test directories
            for subdir in ["uploads", "outputs", "temp"]:
                dir_path = self.local_storage / subdir
                dir_path.mkdir(parents=True, exist_ok=True)
                os.chmod(dir_path, 0o777)
                
                # Test write permissions
                test_file = dir_path / "test.txt"
                test_file.write_text("test")
                test_file.unlink()
                
                logger.info(f"Created and verified directory: {dir_path}")
            
            return True
        except Exception as e:
            logger.error(f"Storage setup failed: {e}")
            return False

    def test_pdf_locally(self):
        """Test PDF conversion locally"""
        try:
            logger.info(f"Testing local PDF processing: {self.test_pdf_path}")
            
            # Verify input file
            if not os.path.exists(self.test_pdf_path):
                raise Exception(f"Test PDF not found: {self.test_pdf_path}")
            
            # Setup paths
            input_path = self.local_storage / "uploads" / "test_input.pdf"
            output_path = self.local_storage / "outputs" / "test_output.pdf"
            
            # Copy test file
            shutil.copy2(self.test_pdf_path, input_path)
            logger.info(f"Copied test file to: {input_path}")
            
            # Process PDF
            target_width = 4 * 72
            target_height = 6 * 72
            margin_mm = -24
            margin_points = margin_mm * 2.83465
            
            src = fitz.open(input_path)
            doc = fitz.open()
            
            for page_num in range(len(src)):
                logger.info(f"Processing page {page_num + 1}/{len(src)}")
                page = src[page_num]
                width = page.rect.width
                start_x = (width / 2) - margin_points
                
                new_page = doc.new_page(width=target_width, height=target_height)
                src_rect = fitz.Rect(start_x, 0, width, page.rect.height)
                target_rect = fitz.Rect(0, 0, target_width, target_height)
                new_page.show_pdf_page(target_rect, src, page_num, clip=src_rect)
            
            doc.save(output_path)
            doc.close()
            src.close()
            
            logger.info(f"Created output file: {output_path}")
            logger.info(f"Output file size: {output_path.stat().st_size} bytes")
            
            return True
            
        except Exception as e:
            logger.error(f"Local PDF processing failed: {e}")
            return False

    def test_api_endpoints(self):
        """Test all API endpoints"""
        try:
            # Test root endpoint
            logger.info("Testing root endpoint")
            response = requests.get(f"{self.api_url}/")
            logger.info(f"Root endpoint response: {response.status_code}")
            logger.info(f"Root endpoint content: {response.text}")
            
            # Test health endpoint
            logger.info("\nTesting health endpoint")
            response = requests.get(f"{self.api_url}/health")
            logger.info(f"Health endpoint response: {response.status_code}")
            logger.info(f"Health endpoint content: {response.text}")
            
            return True
        except Exception as e:
            logger.error(f"API endpoint test failed: {e}")
            return False

    def test_pdf_conversion_api(self):
        """Test PDF conversion through API"""
        try:
            logger.info("\nTesting PDF conversion API")
            
            # Verify test file
            if not os.path.exists(self.test_pdf_path):
                raise Exception("Test PDF file not found")
            
            # Prepare request
            files = {'file': open(self.test_pdf_path, 'rb')}
            data = {'margin_mm': -24}
            
            # Make request
            response = requests.post(
                f"{self.api_url}/api/convert",
                files=files,
                data=data
            )
            
            logger.info(f"Conversion response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                # Check if content type is PDF
                if response.headers.get('Content-Type') == 'application/pdf':
                    # Save response to file
                    output_path = self.local_storage / "api_output.pdf"
                    output_path.write_bytes(response.content)
                    logger.info(f"Saved API response to: {output_path}")
                    logger.info(f"Output file size: {output_path.stat().st_size} bytes")
                else:
                    logger.error("Response is not a PDF file.")
                    return False
                
                return True
            else:
                logger.error(f"API error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"API conversion test failed: {e}")
            return False

    def cleanup(self):
        """Clean up test files"""
        try:
            if self.local_storage.exists():
                shutil.rmtree(self.local_storage)
                logger.info("Cleaned up test storage")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        try:
            # Setup
            logger.info("Starting tests...")
            self.cleanup()  # Clean any previous test files
            
            # Run tests
            storage_ok = self.setup_local_storage()
            logger.info(f"Storage setup: {'✓' if storage_ok else '✗'}")
            
            local_pdf_ok = self.test_pdf_locally()
            logger.info(f"Local PDF processing: {'✓' if local_pdf_ok else '✗'}")
            
            api_endpoints_ok = self.test_api_endpoints()
            logger.info(f"API endpoints: {'✓' if api_endpoints_ok else '✗'}")
            
            conversion_ok = self.test_pdf_conversion_api()
            logger.info(f"PDF conversion API: {'✓' if conversion_ok else '✗'}")
            
        finally:
            # Cleanup
            self.cleanup()

if __name__ == "__main__":
    tester = PDFConverterTester()
    tester.run_all_tests()
